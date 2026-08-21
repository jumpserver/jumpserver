import json
import os
import shutil
from collections import defaultdict
from copy import deepcopy

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import SSHKeyStrategy, SecretStrategy, SecretType, ChangeSecretRecordStatusChoice, \
    ChangeSecretAccountStatus
from accounts.models import Account
from accounts.utils import SecretGenerator, account_secret_task_status
from assets.automations.base.manager import BasePlaybookManager
from assets.const import HostTypes
from common.const import Status
from common.db.utils import safe_atomic_db_connection
from common.utils import get_logger

logger = get_logger(__name__)


class AccountBasePlaybookManager(BasePlaybookManager):
    template_path = ''

    @staticmethod
    def changes_execution_account(runner):
        try:
            with open(runner.inventory, 'r') as inventory_file:
                inventory = json.load(inventory_file)
        except (OSError, TypeError, ValueError):
            return False

        hosts = inventory.get('all', {}).get('hosts', {})
        for detail in hosts.values():
            target = (detail.get('account') or {}).get('username')
            execution = (
                (detail.get('jms_account') or {}).get('username')
                or detail.get('ansible_user')
            )
            if (
                    target and execution
                    and str(target).casefold() == str(execution).casefold()
            ):
                return True
        return False

    @staticmethod
    def configure_runner_environment(runner):
        BasePlaybookManager.configure_runner_environment(runner)
        # Account automations represent every account as an Ansible host. The
        # hosts can share one physical asset and one privileged account, so
        # re-authenticating for every task creates dozens of identical SSH
        # logins. Serialize creation of the first connection and reuse it for
        # the remaining operations on that endpoint.
        if not AccountBasePlaybookManager.changes_execution_account(runner):
            runner.envs.setdefault(
                'ANSIBLE_SSH_ARGS',
                '-C -o ControlMaster=auto -o ControlPersist=60s',
            )
        wrapper_source = os.path.join(
            settings.APPS_DIR, 'ops', 'ansible', 'serialized_ssh.py'
        )
        wrapper_dir = os.path.join(
            runner.project_dir, '.serialized-ssh'
        )
        os.makedirs(wrapper_dir, mode=0o700, exist_ok=True)
        for client in ('ssh', 'scp', 'sftp'):
            wrapper_path = os.path.join(wrapper_dir, client)
            shutil.copyfile(wrapper_source, wrapper_path)
            os.chmod(wrapper_path, 0o700)
            runner.envs[f'ANSIBLE_{client.upper()}_EXECUTABLE'] = (
                wrapper_path
            )

    def get_target_summary(self):
        account_count = len(set(map(
            str, self.execution.snapshot.get('accounts', [])
        )))
        asset_count = len(set(map(
            str, self.execution.snapshot.get('assets', [])
        )))
        return _(
            "Targets: %(accounts)s account(s) on %(assets)s asset(s)"
        ) % {
            'accounts': account_count,
            'assets': asset_count,
        }

    def get_execution_asset_source_ids(self):
        source_asset_ids_by_asset_id = getattr(
            self, '_source_asset_ids_by_asset_id', None
        )
        if source_asset_ids_by_asset_id is not None:
            return source_asset_ids_by_asset_id

        # An asset can use accounts from joined directory services. Keep the
        # same source set as Asset.all_accounts without querying that relation
        # repeatedly while generating a large inventory.
        asset_ids = {
            str(asset_id)
            for asset_id in self.execution.get_all_asset_ids()
        }
        source_asset_ids_by_asset_id = {
            asset_id: {asset_id} for asset_id in asset_ids
        }
        from assets.models import Asset
        relations = Asset.directory_services.through.objects.filter(
            asset_id__in=asset_ids
        ).values_list('asset_id', 'directoryservice_id')
        for asset_id, directory_service_id in relations:
            source_asset_ids_by_asset_id[str(asset_id)].add(
                str(directory_service_id)
            )
        self._source_asset_ids_by_asset_id = source_asset_ids_by_asset_id
        return source_asset_ids_by_asset_id

    def index_accounts_by_execution_asset(self, accounts, include_related=True):
        if include_related:
            accounts = accounts.select_related(
                'asset__platform', 'asset__ds', 'su_from',
                'su_from__asset__platform', 'su_from__asset__ds',
            )

        accounts_by_source_asset_id = defaultdict(list)
        for account in accounts:
            accounts_by_source_asset_id[str(account.asset_id)].append(account)

        accounts_by_asset_id = defaultdict(list)
        for asset_id, source_asset_ids in (
                self.get_execution_asset_source_ids().items()
        ):
            for source_asset_id in source_asset_ids:
                accounts_by_asset_id[asset_id].extend(
                    accounts_by_source_asset_id[source_asset_id]
                )
        return accounts_by_asset_id

    @property
    def platform_automation_methods(self):
        from assets.const import AllTypes
        return AllTypes.get_automation_methods()


class BaseChangeSecretPushManager(AccountBasePlaybookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_type = self.execution.snapshot.get('secret_type')
        self.secret_strategy = self.execution.snapshot.get(
            'secret_strategy', SecretStrategy.custom
        )
        self.ssh_key_change_strategy = self.execution.snapshot.get(
            'ssh_key_change_strategy', SSHKeyStrategy.set_jms
        )
        self.account_ids = self.execution.snapshot['accounts']
        self.record_map = self.execution.snapshot.get('record_map', {})  # 这个是某个失败的记录重试
        self.name_record_mapper = {}  # 做个映射，方便后面处理
        self.inventory_account_mapper = {}
        self.account_locks = {}
        self.found_account_ids = set()
        self._accounts_by_asset_id = None
        self._target_account_ids_by_asset_id = None

    @staticmethod
    def get_record_result_counts(records):
        success = failed = unverified = 0
        for record in records:
            if record.status == ChangeSecretRecordStatusChoice.success.value:
                success += 1
            elif record.status == ChangeSecretRecordStatusChoice.unverified.value:
                unverified += 1
            else:
                failed += 1
        return success, failed, unverified

    def get_host_success_log(self, host):
        return None, None

    def print_final_host_result(self, host, record):
        host = self.get_host_display_label(host)
        if (
                record
                and record.status
                == ChangeSecretRecordStatusChoice.unverified.value
        ):
            self.print_log(_(
                "△ %(host)s: operation completed; verification pending"
            ) % {'host': host}, 'progress')
            return

        if str(self.method_type()) == 'change_secret':
            result = _("secret changed and verified")
        else:
            result = _("account pushed and verified")
        self.print_log(_("✓ %(host)s: %(result)s") % {
            'host': host,
            'result': result,
        }, 'success')

    def gen_account_inventory(self, account, asset, h, path_dir):
        raise NotImplementedError

    def get_ssh_params(self, secret, secret_type):
        kwargs = {}
        if secret_type != SecretType.SSH_KEY:
            return kwargs
        kwargs['strategy'] = self.ssh_key_change_strategy
        kwargs['exclusive'] = 'yes' if kwargs['strategy'] == SSHKeyStrategy.set else 'no'

        if kwargs['strategy'] == SSHKeyStrategy.set_jms:
            kwargs['regexp'] = '.*{}$'.format(secret.split()[2].strip())
        return kwargs

    def get_secret(self, account):
        if self.secret_strategy == SecretStrategy.custom:
            new_secret = self.execution.snapshot.get('secret')
        else:
            generator = SecretGenerator(
                self.secret_strategy, self.secret_type,
                self.execution.snapshot.get('password_rules')
            )
            new_secret = generator.get_secret()
        return new_secret

    def load_accounts_by_asset(self):
        if self._accounts_by_asset_id is not None:
            return

        accounts = Account.objects.filter(
            id__in=self.account_ids,
            secret_reset=True,
        )
        if self.secret_type:
            accounts = accounts.filter(secret_type=self.secret_type)
        if settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED:
            accounts = accounts.filter(privileged=False).exclude(
                username__in=['root', 'administrator']
            )

        # Account automation can target a large node. Loading the eligible
        # accounts once avoids issuing the complete account-id IN query again
        # for every asset while inventories are prepared.
        accounts_by_asset_id = self.index_accounts_by_execution_asset(accounts)

        target_account_ids_by_asset_id = defaultdict(set)
        target_accounts_by_asset_id = self.index_accounts_by_execution_asset(
            Account.objects.filter(id__in=self.account_ids).only(
                'id', 'asset_id'
            ),
            include_related=False,
        )
        for asset_id, target_accounts in target_accounts_by_asset_id.items():
            target_account_ids_by_asset_id[asset_id].update(
                str(account.id) for account in target_accounts
            )

        self._accounts_by_asset_id = accounts_by_asset_id
        self._target_account_ids_by_asset_id = target_account_ids_by_asset_id

    def get_accounts(self, privilege_account):
        if not privilege_account:
            print(_('No privileged account'))
            return []

        self.load_accounts_by_asset()
        accounts = self._accounts_by_asset_id.get(
            str(privilege_account.asset_id), []
        )
        if settings.CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED:
            accounts = [
                account for account in accounts
                if account.username != privilege_account.username
            ]
        return accounts

    def get_target_account_ids(self, asset_id):
        self.load_accounts_by_asset()
        return self._target_account_ids_by_asset_id.get(str(asset_id), set())

    def handle_ssh_secret(self, secret_type, new_secret, path_dir):
        private_key_path = None
        if secret_type == SecretType.SSH_KEY:
            private_key_path = self.generate_private_key_path(new_secret, path_dir)
            new_secret = self.generate_public_key(new_secret)
        return new_secret, private_key_path

    def gen_inventory(self, h, account, new_secret, private_key_path, asset):
        secret_type = account.secret_type
        h['ssh_params'].update(self.get_ssh_params(new_secret, secret_type))
        h['account'] = {
            'name': account.name,
            'username': account.username,
            'full_username': account.full_username,
            'secret_type': secret_type,
            'secret': account.escape_jinja2_syntax(new_secret),
            'private_key_path': private_key_path,
            'become': account.get_ansible_become_auth(),
        }
        if asset.platform.type == 'oracle':
            use_sysdba = (
                account.privileged and
                h['jms_asset'].get('oracle_sysdba', False)
            )
            h['account']['mode'] = 'sysdba' if use_sysdba else None
        return h

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(
            host, asset=asset, account=account, automation=automation,
            path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            return host

        inventory_hosts = []
        if asset.type == HostTypes.WINDOWS:
            if self.secret_type == SecretType.SSH_KEY:
                host['error'] = _("Windows does not support SSH key authentication")
                return host

        host['ssh_params'] = {}

        accounts = self.get_accounts(account)
        existing_ids = {str(account.id) for account in accounts}
        self.found_account_ids.update(existing_ids)
        # `self.account_ids` covers the complete execution. Comparing it
        # directly with one asset's accounts releases statuses/locks already
        # prepared for other assets in the same execution.
        target_ids = self.get_target_account_ids(asset.id)
        missing_ids = target_ids - existing_ids

        for account_id in missing_ids:
            self.clear_account_queue_status(account_id)

        error_msg = _("No pending accounts found")
        if not accounts:
            self.result['skipped_assets'].append({
                'asset': str(asset),
                'reason': str(error_msg),
            })
            self.print_log(_(
                "○ %(asset)s: skipped; no eligible accounts"
            ) % {'asset': self.format_asset_label(asset)}, 'progress')
            return []

        if asset.type == HostTypes.WINDOWS:
            accounts = [
                account for account in accounts
                if account.secret_type == SecretType.PASSWORD
            ]

        for account in accounts:
            h = deepcopy(host)
            h['name'] += '(' + account.username + ')'  # To distinguish different accounts
            self.inventory_account_mapper[h['name']] = account
            h['account'] = {
                'username': account.username,
                'full_username': account.full_username,
            }

            try:
                if not self.acquire_account_lock(account.id):
                    h['error'] = _(
                        'Account is already being processed, skipping: %(account)s'
                    ) % {'account': account}
                    inventory_hosts.append(h)
                    continue

                h, record = self.gen_account_inventory(account, asset, h, path_dir)
                h['check_conn_after_change'] = record.execution.snapshot.get('check_conn_after_change', True)
                account_secret_task_status.set_status(
                    account.id,
                    ChangeSecretAccountStatus.PROCESSING,
                    timeout=self.get_account_lock_expire(),
                    metadata={'execution_id': str(self.execution.id)}
                )
            except Exception as e:
                h['error'] = str(e)
                self.clear_account_queue_status(account.id)

            inventory_hosts.append(h)

        return inventory_hosts

    def get_runners(self):
        runners = super().get_runners()
        missing_account_ids = (
            set(map(str, self.account_ids)) - self.found_account_ids
        )
        for account_id in sorted(missing_account_ids):
            self.clear_account_queue_status(account_id)
            error = str(_(
                'Account not found, inactive, or not eligible for this task'
            ))
            self.summary['fail_accounts'] += 1
            self.result['fail_accounts'].append({
                'asset': '',
                'username': account_id,
                'error': error,
            })
            self.print_inventory_host_error(account_id, error)
        return runners

    @staticmethod
    def save_record(record):
        record.save(update_fields=['error', 'status', 'date_finished'])

    @staticmethod
    def get_account_lock_expire():
        total_timeout = int(
            getattr(settings, 'ANSIBLE_AUTOMATION_TOTAL_TIMEOUT', 21600)
            or 0
        )
        return max(total_timeout + 600, 3600) if total_timeout else 86400

    def acquire_account_lock(self, account_id):
        account_id = str(account_id)
        if account_id in self.account_locks:
            return True

        lock = cache.lock(
            f'account-change-secret:{account_id}',
            expire=self.get_account_lock_expire(),
            id=str(self.execution.id),
            auto_renewal=False,
        )
        acquired = lock.acquire(blocking=False)
        if acquired:
            self.account_locks[account_id] = lock
        return acquired

    def release_account_lock(self, account_id):
        lock = self.account_locks.pop(str(account_id), None)
        if not lock:
            return
        try:
            lock.release()
        except Exception:
            logger.exception(
                'Release account change-secret lock failed: account=%s',
                account_id,
            )

    def release_all_account_locks(self):
        for account_id in list(self.account_locks):
            self.release_account_lock(account_id)

    def clear_account_queue_status(self, account_id):
        try:
            metadata = account_secret_task_status.get(account_id) or {}
            owner = str(metadata.get('execution_id') or '')
            if not owner or owner == str(self.execution.id):
                account_secret_task_status.clear(account_id)
        finally:
            self.release_account_lock(account_id)

    @staticmethod
    def get_inconclusive_probe(result):
        result = result or {}
        # BaseManager._on_host_success passes the current host's `ok` task
        # mapping, while some direct callers may pass the full host result.
        # Support both shapes so delegated ssh_ping results are not missed.
        ok_results = result.get('ok')
        if ok_results is None:
            ok_results = result
        for task_result in ok_results.values():
            probe_result = task_result.get('res', {})
            fact_probe = (
                probe_result.get('ansible_facts', {})
                .get('jms_credential_probe')
            )
            if fact_probe:
                probe_result = fact_probe
            if probe_result.get('auth_status') == 'unknown':
                return probe_result
        return None

    @staticmethod
    def should_sync_candidate(inconclusive_probe):
        # An inconclusive independent probe must never replace the last known
        # credential with an unverified candidate.
        return inconclusive_probe is None

    def move_account_result(self, source_key, target_key, item):
        if source_key == target_key:
            return
        self.summary[source_key] = max(
            0, self.summary[source_key] - 1
        )
        try:
            self.result[source_key].remove(item)
        except ValueError:
            pass
        self.summary[target_key] += 1
        self.result[target_key].append(item)

    def persist_record_fallback(self, record):
        record.__class__.objects.filter(id=record.id).update(
            status=record.status,
            error=record.error,
            date_finished=record.date_finished,
        )

    def on_host_success(self, host, result):
        record = self.name_record_mapper.get(host)
        if not record:
            return
        inconclusive_probe = self.get_inconclusive_probe(result)
        if inconclusive_probe:
            record.status = ChangeSecretRecordStatusChoice.unverified.value
            reason_code = inconclusive_probe.get('reason_code', 'PROBE_ERROR')
            record.error = _(
                'The remote secret may have changed, but the independent '
                'credential verification was inconclusive: %(code)s'
            ) % {'code': reason_code}
        else:
            record.status = ChangeSecretRecordStatusChoice.success.value
            record.error = ''
        record.date_finished = timezone.now()

        account = record.account
        if not account:
            result_key = (
                'unverified_accounts'
                if inconclusive_probe
                else 'ok_accounts'
            )
            self.summary[result_key] += 1
            self.result[result_key].append({
                "asset": str(record.asset),
                "username": record.comment or '',
            })
            super().on_host_success(host, result)
            try:
                self.save_record(record)
            except Exception:
                self.status = Status.error
                logger.exception(
                    'Save account result without local account failed: '
                    'record=%s host=%s',
                    getattr(record, 'id', None), host,
                )
                record.status = ChangeSecretRecordStatusChoice.unverified.value
            self.print_final_host_result(host, record)
            inventory_account = self.inventory_account_mapper.get(host)
            if inventory_account:
                self.clear_account_queue_status(inventory_account.id)
            return

        update_fields = ['date_updated', 'date_change_secret', 'change_secret_status']
        should_sync_candidate = self.should_sync_candidate(
            inconclusive_probe
        )
        if hasattr(record, 'new_secret') and should_sync_candidate:
            account.secret = record.new_secret
            update_fields.insert(0, 'secret')
        account.date_updated = timezone.now()
        account.date_change_secret = timezone.now()
        account.change_secret_status = record.status

        result_key = (
            'unverified_accounts'
            if inconclusive_probe
            else 'ok_accounts'
        )
        result_item = {
            "asset": str(account.asset),
            "username": account.username,
        }
        self.summary[result_key] += 1
        self.result[result_key].append(result_item)
        super().on_host_success(host, result)

        with safe_atomic_db_connection():
            try:
                with transaction.atomic():
                    account.save(update_fields=update_fields)
                    self.save_record(record)
            except Exception as error:
                logger.exception(
                    'Save account success result failed: account=%s, record=%s, host=%s',
                    account.id, getattr(record, 'id', None), host
                )
                self.status = Status.error
                record.status = (
                    ChangeSecretRecordStatusChoice.unverified.value
                )
                record.error = _(
                    'The remote operation completed, but saving the local '
                    'account result failed: %(error)s'
                ) % {'error': str(error)}
                record.date_finished = timezone.now()
                account.change_secret_status = record.status
                target_key = 'unverified_accounts'
                self.move_account_result(
                    result_key, target_key, result_item
                )
                try:
                    self.persist_record_fallback(record)
                except Exception:
                    logger.exception(
                        'Fallback save account result failed: record=%s',
                        getattr(record, 'id', None),
                    )
            finally:
                self.clear_account_queue_status(account.id)
        self.print_final_host_result(host, record)

    def finalize_incomplete_record(self, record, error):
        if record.status != ChangeSecretRecordStatusChoice.pending.value:
            return

        status = ChangeSecretRecordStatusChoice.unverified.value
        record.status = status
        record.error = str(error)
        record.date_finished = timezone.now()

        account = record.account
        result_key = 'unverified_accounts'
        self.summary[result_key] += 1
        self.result[result_key].append(
            {
                "asset": str(record.asset),
                "username": account.username if account else '',
            }
        )

        with safe_atomic_db_connection():
            try:
                with transaction.atomic():
                    self.save_record(record)
                    if account:
                        # QuerySet.update avoids Account.save and its remote
                        # vault write while keeping the account-level status
                        # consistent with the record.
                        Account.objects.filter(id=account.id).update(
                            change_secret_status=status
                        )
            except Exception:
                self.status = Status.error
                logger.exception(
                    'Save incomplete account result failed: record=%s',
                    getattr(record, 'id', None),
                )
                try:
                    self.persist_record_fallback(record)
                except Exception:
                    logger.exception(
                        'Fallback save incomplete account result failed: record=%s',
                        getattr(record, 'id', None),
                    )
            finally:
                if account:
                    self.clear_account_queue_status(account.id)

    def on_host_incomplete(self, host, error):
        record = self.name_record_mapper.get(host)
        if not record:
            return super().on_host_incomplete(host, error)
        self.finalize_incomplete_record(record, error)

    def on_inventory_host_error(self, host, error):
        if host in self.name_record_mapper:
            return self.on_host_error(host, error, {})
        account = self.inventory_account_mapper.get(host)
        if account:
            self.summary['fail_accounts'] += 1
            self.result['fail_accounts'].append({
                'asset': str(account.asset),
                'username': account.username,
                'error': str(error),
            })
            self.clear_account_queue_status(account.id)
            label = self._inventory_host_labels.get(host, host)
            self.print_inventory_host_error(label, error)
            return
        return super().on_inventory_host_error(host, error)

    def finalize_pending_records(self):
        seen = set()
        pending_records = []
        for record in self.name_record_mapper.values():
            record_id = str(record.id)
            if record_id in seen:
                continue
            seen.add(record_id)
            if record.status == ChangeSecretRecordStatusChoice.pending.value:
                pending_records.append(record)

        if not pending_records:
            return

        if self.status not in (Status.canceled, Status.error):
            self.status = Status.failed
        error = (
            self.interruption_reason
            or str(_("Task ended before the account received a final result"))
        )
        date_finished = timezone.now()
        grouped_records = {}
        for record in pending_records:
            status = ChangeSecretRecordStatusChoice.unverified.value
            group_key = (record.__class__, status)
            grouped_records.setdefault(group_key, []).append(record)

            record.status = status
            record.error = error
            record.date_finished = date_finished

            result_key = 'unverified_accounts'
            self.summary[result_key] += 1
            self.result[result_key].append(
                {
                    "asset": str(record.asset),
                    "username": (
                        record.account.username if record.account else ''
                    ),
                }
            )
            if record.account_id:
                self.clear_account_queue_status(record.account_id)

        # Records for batches that never started can be finalized in bulk.
        # Avoid saving every Account here: Account.save triggers an external
        # vault write, which would make canceling a 2,000-account task slow.
        account_ids = [
            record.account_id
            for record in pending_records
            if record.account_id
        ]
        Account.objects.filter(id__in=account_ids).update(
            change_secret_status=(
                ChangeSecretRecordStatusChoice.unverified.value
            )
        )
        for (model, status), records in grouped_records.items():
            record_ids = [record.id for record in records]
            model.objects.filter(
                id__in=record_ids,
                status=ChangeSecretRecordStatusChoice.pending.value,
            ).update(
                status=status,
                error=error,
                date_finished=date_finished,
            )

    def post_run(self):
        try:
            self.finalize_pending_records()
        except Exception:
            logger.exception(
                'Finalize pending account records failed: execution=%s',
                self.execution.id,
            )
            if self.status != Status.canceled:
                self.status = Status.error
        finally:
            try:
                super().post_run()
            finally:
                self.release_all_account_locks()

    def on_host_error(self, host, error, result):
        record = self.name_record_mapper.get(host)
        if not record:
            return
        record.status = ChangeSecretRecordStatusChoice.failed.value
        record.date_finished = timezone.now()
        record.error = error
        account = record.account
        if not account:
            self.summary['fail_accounts'] += 1
            self.result['fail_accounts'].append({
                "asset": str(record.asset),
                "username": record.comment or '',
                "error": str(error),
            })
            super().on_host_error(host, error, result)
            try:
                self.save_record(record)
            except Exception:
                self.status = Status.error
                logger.exception(
                    'Save failed account result without local account failed: '
                    'record=%s host=%s',
                    getattr(record, 'id', None), host,
                )
            inventory_account = self.inventory_account_mapper.get(host)
            if inventory_account:
                self.clear_account_queue_status(inventory_account.id)
            return
        account.date_updated = timezone.now()
        account.date_change_secret = timezone.now()
        account.change_secret_status = ChangeSecretRecordStatusChoice.failed

        self.summary['fail_accounts'] += 1
        self.result['fail_accounts'].append(
            {
                "asset": str(record.asset),
                "username": record.account.username,
                "error": str(error),
            }
        )
        super().on_host_error(host, error, result)

        with safe_atomic_db_connection():
            try:
                with transaction.atomic():
                    account.save(
                        update_fields=[
                            'change_secret_status',
                            'date_change_secret',
                            'date_updated',
                        ]
                    )
                    self.save_record(record)
            except Exception:
                self.status = Status.error
                logger.exception(
                    'Save account failure result failed: account=%s, record=%s, host=%s',
                    account.id, getattr(record, 'id', None), host,
                )
                try:
                    self.persist_record_fallback(record)
                except Exception:
                    logger.exception(
                        'Fallback save account failure result failed: record=%s',
                        getattr(record, 'id', None),
                    )
            finally:
                self.clear_account_queue_status(account.id)
