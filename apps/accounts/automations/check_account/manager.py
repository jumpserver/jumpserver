import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import tempfile
from itertools import islice

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Account, AccountRisk, RiskChoice, SecretType
from assets.automations.base.manager import BaseManager
from common.const import ConfirmOrIgnore, Status
from common.utils.lock import DistributedLock
from settings.models import LeakPasswords


class BaseCheckHandler:
    risk = ''

    def check(self, secret):
        raise NotImplementedError

    def clean(self):
        pass


class CheckSecretHandler(BaseCheckHandler):
    risk = RiskChoice.weak_password

    @staticmethod
    def is_weak_password(password):
        # 判断密码长度
        if len(password) < 8:
            return True

        # 判断是否只有一种字符类型
        if password.isdigit() or password.isalpha():
            return True

        # 判断是否只包含数字或字母
        if password.islower() or password.isupper():
            return True

        # 判断是否包含常见弱密码
        common_passwords = [
            "123456", "password", "12345678", "qwerty", "abc123",
        ]
        if password.lower() in common_passwords:
            return True

        # 正则表达式判断字符多样性（数字、字母、特殊字符）
        has_alpha = re.search(r"[A-Za-z]", password)
        has_digit = re.search(r"[0-9]", password)
        has_special = re.search(r"[\W_]", password)
        return not (has_alpha and has_digit and has_special)

    def check(self, secret):
        return bool(secret) and self.is_weak_password(secret)


class CheckRepeatHandler(BaseCheckHandler):
    risk = RiskChoice.repeated_password
    scan_batch_size = 500

    def __init__(self):
        # A per-run HMAC key keeps equality checks possible without retaining
        # plaintext passwords or reusable password digests in memory.
        self.digest_key = secrets.token_bytes(32)
        self.repeated_digests = self.load_repeated_digests()

    def digest(self, secret):
        return hmac.digest(
            self.digest_key, secret.encode(), hashlib.sha256
        )

    def load_repeated_digests(self):
        tmp_file = tempfile.NamedTemporaryFile(
            prefix='account_password_digests_', suffix='.db', delete=False
        )
        path = tmp_file.name
        tmp_file.close()
        connection = None
        try:
            connection = sqlite3.connect(path)
            connection.execute('PRAGMA journal_mode=OFF')
            connection.execute('PRAGMA synchronous=OFF')
            connection.execute(
                'CREATE TABLE digests ('
                'digest BLOB PRIMARY KEY, amount INTEGER NOT NULL'
                ')'
            )
            sql = (
                'INSERT INTO digests (digest, amount) VALUES (?, 1) '
                'ON CONFLICT(digest) DO UPDATE SET amount = amount + 1'
            )
            accounts = (
                Account.objects.filter(secret_type=SecretType.PASSWORD)
                .only('id', '_secret', 'secret_type', 'asset_id', 'org_id')
                .iterator(chunk_size=self.scan_batch_size)
            )
            digests = []
            for account in accounts:
                secret = account.secret
                if not secret:
                    continue
                digests.append((self.digest(secret),))
                if len(digests) >= self.scan_batch_size:
                    connection.executemany(sql, digests)
                    digests.clear()
            if digests:
                connection.executemany(sql, digests)
            connection.commit()
            return {
                row[0] for row in connection.execute(
                    'SELECT digest FROM digests WHERE amount > 1'
                )
            }
        finally:
            if connection is not None:
                connection.close()
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def check(self, secret):
        if not secret:
            return False
        return self.digest(secret) in self.repeated_digests

    def clean(self):
        self.digest_key = b''
        self.repeated_digests.clear()


class CheckLeakHandler(BaseCheckHandler):
    risk = RiskChoice.leaked_password
    scan_batch_size = 2000

    def __init__(self):
        self.leaked_passwords = set(
            LeakPasswords.objects.using('sqlite')
            .values_list('password', flat=True)
            .iterator(chunk_size=self.scan_batch_size)
        )

    def check(self, secret):
        return bool(secret) and secret in self.leaked_passwords

    def clean(self):
        self.leaked_passwords.clear()


class CheckAccountManager(BaseManager):
    account_batch_size = 500
    result_limit = 300
    log_result_limit = 50
    supported_engines = {
        'check_account_secret': CheckSecretHandler,
        'check_account_repeat': CheckRepeatHandler,
        'check_account_leak': CheckLeakHandler,
    }
    handler_labels = {
        CheckSecretHandler: _('Password strength'),
        CheckRepeatHandler: _('Repeated password'),
        CheckLeakHandler: _('Leaked password'),
    }
    risk_labels = {
        RiskChoice.weak_password: _('Weak password'),
        RiskChoice.repeated_password: _('Repeated password'),
        RiskChoice.leaked_password: _('Leaked password'),
    }

    def __init__(self, execution):
        super().__init__(execution)
        self.asset_ids = []
        self.handlers = []
        self.checked_accounts = 0
        self.risky_accounts = 0
        self.no_secret_accounts = 0
        self.ok_accounts = 0

    def pre_run(self):
        super().pre_run()
        self.asset_ids = list(
            self.execution.get_all_assets().values_list('id', flat=True)
        )

    def get_engine_names(self):
        engines = self.execution.snapshot.get('engines') or []
        if engines == '__all__':
            return list(self.supported_engines)

        engine_names = []
        for engine in engines:
            if engine not in self.supported_engines:
                logging.warning(
                    'Unknown account security check: %s', engine
                )
                continue
            if engine not in engine_names:
                engine_names.append(engine)

        if not engine_names:
            raise ValueError(_(
                'No supported account security check selected'
            ))
        return engine_names

    def init_handlers(self, engine_names):
        for engine in engine_names:
            handler = self.supported_engines[engine]()
            self.handlers.append(handler)
            label = self.handler_labels.get(
                handler.__class__, _('Account security')
            )
            label = str(label).rstrip(':：')
            self.print_log(
                _("Enabled account security check: %(check)s") % {
                    'check': label,
                },
                'progress',
            )

    def cleanup_non_password_risks(self, engine_names):
        password_accounts = Account.objects.filter(
            asset_id=OuterRef('asset_id'),
            username=OuterRef('username'),
            secret_type=SecretType.PASSWORD,
        )
        risks = [
            str(self.supported_engines[engine].risk)
            for engine in engine_names
        ]
        (
            AccountRisk.objects.filter(
                asset_id__in=self.asset_ids,
                risk__in=risks,
            )
            .annotate(has_password_account=Exists(password_accounts))
            .filter(has_password_account=False)
            .delete()
        )

    @staticmethod
    def iter_batches(queryset, batch_size):
        iterator = queryset.iterator(chunk_size=batch_size)
        while True:
            batch = list(islice(iterator, batch_size))
            if not batch:
                return
            yield batch

    def add_result(self, risk, account):
        self.summary[risk] += 1
        if len(self.result[risk]) >= self.result_limit:
            return
        asset_label = str(account.asset)
        address = account.asset.address
        if address and str(address) not in asset_label:
            asset_label = f'{asset_label}[{address}]'
        self.result[risk].append({
            'asset_id': str(account.asset_id),
            'asset': asset_label,
            'username': account.username,
        })

    @staticmethod
    def risk_key(asset_id, username, risk):
        return str(asset_id), username, str(risk)

    def reconcile_risks(self, accounts, findings):
        if not accounts:
            return

        account_by_key = {
            (str(account.asset_id), account.username): account
            for account in accounts
        }
        asset_ids = {account.asset_id for account in accounts}
        usernames = {account.username for account in accounts}
        enabled_risks = [str(handler.risk) for handler in self.handlers]
        existing_risks = AccountRisk.objects.filter(
            asset_id__in=asset_ids,
            username__in=usernames,
            risk__in=enabled_risks,
        )
        existing_map = {
            self.risk_key(risk.asset_id, risk.username, risk.risk): risk
            for risk in existing_risks
            if (str(risk.asset_id), risk.username) in account_by_key
        }

        desired = {}
        for account, risks in findings:
            for risk in risks:
                key = self.risk_key(account.asset_id, account.username, risk)
                desired[key] = account

        delete_ids = [
            risk.id for key, risk in existing_map.items()
            if key not in desired
        ]
        to_create = []
        to_update = []
        now = timezone.now().isoformat()

        for key, account in desired.items():
            risk = existing_map.get(key)
            if risk is None:
                to_create.append(AccountRisk(
                    account=account,
                    asset_id=account.asset_id,
                    username=account.username,
                    risk=key[2],
                    details=[{'datetime': now, 'type': 'init'}],
                ))
                continue

            changed = False
            if risk.account_id != account.id:
                risk.account = account
                changed = True
            if risk.status != ConfirmOrIgnore.pending:
                details = risk.details or []
                details.append({'datetime': now, 'type': 'refind'})
                if len(details) > 100:
                    details = [*details[:5], *details[-5:]]
                risk.details = details
                risk.status = ConfirmOrIgnore.pending
                changed = True
            if changed:
                to_update.append(risk)

        with transaction.atomic():
            if delete_ids:
                AccountRisk.objects.filter(id__in=delete_ids).delete()
            if to_create:
                AccountRisk.objects.bulk_create(
                    to_create, ignore_conflicts=True
                )
            if to_update:
                AccountRisk.objects.bulk_update(
                    to_update, ['account', 'details', 'status']
                )

    def check_batch(self, accounts):
        findings = []
        for account in accounts:
            self.checked_accounts += 1
            secret = account.secret
            if not secret:
                self.no_secret_accounts += 1

            account_risks = [
                handler.risk for handler in self.handlers
                if handler.check(secret)
            ]
            for risk in account_risks:
                self.add_result(risk, account)

            if account_risks:
                self.risky_accounts += 1
            elif secret:
                self.ok_accounts += 1
            findings.append((account, account_risks))

        self.reconcile_risks(accounts, findings)

    def run_checks(self):
        engine_names = self.get_engine_names()
        if not self.asset_ids:
            return

        self.init_handlers(engine_names)
        self.cleanup_non_password_risks(engine_names)
        accounts = (
            Account.objects.filter(
                asset_id__in=self.asset_ids,
                secret_type=SecretType.PASSWORD,
            )
            .select_related('asset')
            .order_by('id')
        )
        for batch in self.iter_batches(accounts, self.account_batch_size):
            self.print_log(_("Processing %(count)s accounts") % {
                'count': len(batch),
            }, 'progress')
            self.check_batch(batch)

    def do_run(self, *args, **kwargs):
        lock = DistributedLock(
            'account-risk-check:{}'.format(self.execution.org_id)
        )
        if not lock.acquire(blocking=False):
            raise RuntimeError(_(
                'Another account risk check is already running'
            ))

        try:
            self.run_checks()
        finally:
            lock.release()

        self.summary['no_secret'] = self.no_secret_accounts
        self.summary['ok'] = self.ok_accounts

    def post_run(self):
        for handler in self.handlers:
            try:
                handler.clean()
            except Exception:
                logging.exception(
                    'Clean account check handler failed: %s',
                    handler.__class__.__name__,
                )
                self.status = Status.error
        super().post_run()

    def get_report_subject(self):
        return _("Check account report of {}").format(self.execution.id)

    def get_report_template(self):
        return "accounts/check_account_report.html"

    def print_risk_accounts(self):
        for risk, label in self.risk_labels.items():
            count = self.summary[risk]
            if not count:
                continue

            accounts = self.result[risk][:self.log_result_limit]
            self.print_log(
                '{} ({}):'.format(label, count),
                'error',
            )
            grouped_accounts = {}
            for account in accounts:
                asset_key = (account['asset_id'], account['asset'])
                grouped_accounts.setdefault(asset_key, []).append(
                    account['username']
                )

            groups = sorted(
                grouped_accounts.items(),
                key=lambda item: item[0][1].casefold(),
            )
            for (_, asset), usernames in groups:
                self.print_log(
                    "  - {}: {}".format(
                        asset,
                        ', '.join(sorted(usernames, key=str.casefold)),
                    ),
                    'error',
                )

            omitted = count - len(accounts)
            if omitted > 0:
                self.print_log("  ... +{}".format(omitted), 'error')

    def print_summary(self):
        weak = self.summary[RiskChoice.weak_password]
        leaked = self.summary[RiskChoice.leaked_password]
        repeated = self.summary[RiskChoice.repeated_password]
        execution_failed = self.status in (Status.failed, Status.error)
        self.print_log(
            _("Task execution completed"),
            'error' if execution_failed else 'success',
        )
        self.print_log(_(
            "Checked %(total)s accounts: %(normal)s normal, %(risk)s at risk, "
            "%(no_secret)s without secrets"
        ) % {
            'total': self.checked_accounts,
            'normal': self.ok_accounts,
            'risk': self.risky_accounts,
            'no_secret': self.no_secret_accounts,
        }, 'error' if self.risky_accounts else 'success')
        if self.risky_accounts:
            self.print_log(_(
                "Risk details: %(weak)s weak passwords, %(leaked)s leaked "
                "passwords, %(repeated)s repeated passwords"
            ) % {
                'weak': weak,
                'leaked': leaked,
                'repeated': repeated,
            }, 'error')
            self.print_risk_accounts()
        self.print_log(_("Duration: %(duration)s seconds") % {
            'duration': self.duration,
        }, 'info')
