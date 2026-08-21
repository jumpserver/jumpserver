import os
from copy import deepcopy

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.const import (
    AutomationTypes, ChangeSecretRecordStatusChoice, Connectivity, SecretType,
)
from accounts.models import Account, ChangeSecretRecord
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)


class VerifyAccountManager(AccountBasePlaybookManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = {}
        self.account_ids = set(map(
            str, self.execution.snapshot.get('accounts', [])
        ))
        self.found_account_ids = set()
        self.recovery_record_map = self.execution.snapshot.get(
            'recovery_record_map', {}
        )
        self.recovery_records = {
            str(record.id): record
            for record in ChangeSecretRecord.objects.filter(
                id__in=self.recovery_record_map.values()
            )
        }
        self.host_record_mapper = {}
        self._accounts_by_asset_id = None

    def prepare_runtime_dir(self):
        path = super().prepare_runtime_dir()
        ansible_config_path = os.path.join(path, 'ansible.cfg')

        with open(ansible_config_path, 'w') as f:
            f.write('[ssh_connection]\n')
            f.write('ssh_args = -o ControlMaster=no -o ControlPersist=no\n')
        return path

    @classmethod
    def method_type(cls):
        return AutomationTypes.verify_account

    def load_accounts_by_asset(self):
        if self._accounts_by_asset_id is not None:
            return

        # A large verification task previously evaluated this complete account
        # ID filter once per asset. Load it once, together with the relations
        # needed while building each Ansible inventory.
        accounts = Account.objects.filter(id__in=self.account_ids)
        self._accounts_by_asset_id = self.index_accounts_by_execution_asset(
            accounts
        )

    def get_accounts(self, asset):
        self.load_accounts_by_asset()
        return self._accounts_by_asset_id.get(str(asset.id), [])

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(
            host, asset=asset, account=account,
            automation=automation, path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            return host

        accounts = self.get_accounts(asset)
        inventory_hosts = []

        for account in accounts:
            self.found_account_ids.add(str(account.id))
            h = deepcopy(host)
            h['name'] += '(' + account.username + ')'
            self.host_account_mapper[h['name']] = account
            h['account'] = {
                'username': account.username,
                'full_username': account.full_username,
            }
            record = self.get_recovery_record(asset.id, account.id)
            if self.recovery_record_map and not record:
                h['error'] = str(_(
                    'Change secret record not found or does not match account'
                ))
                inventory_hosts.append(h)
                continue
            if record:
                self.host_record_mapper[h['name']] = record
            secret = record.new_secret if record else account.secret
            if not secret:
                h['error'] = 'Account secret is empty'
                inventory_hosts.append(h)
                continue

            private_key_path = None
            if account.secret_type == SecretType.SSH_KEY:
                private_key_path = self.generate_private_key_path(secret, path_dir)
                secret = self.generate_public_key(secret)

            h['secret_type'] = account.secret_type
            h['account'] = {
                'name': account.name,
                'username': account.username,
                'full_username': account.full_username,
                'secret_type': account.secret_type,
                'secret': account.escape_jinja2_syntax(secret),
                'private_key_path': private_key_path,
                'become': account.get_ansible_become_auth(),
            }
            if account.platform.type == 'oracle':
                use_sysdba = (
                    account.privileged and
                    h['jms_asset'].get('oracle_sysdba', False)
                )
                h['account']['mode'] = 'sysdba' if use_sysdba else None
            inventory_hosts.append(h)
        return inventory_hosts

    def get_recovery_record(self, asset_id, account_id):
        key = f'{asset_id}-{account_id}'
        record_id = self.recovery_record_map.get(key)
        record = self.recovery_records.get(str(record_id))
        if not record:
            return None
        if (
                str(record.asset_id) != str(asset_id)
                or str(record.account_id) != str(account_id)
        ):
            return None
        return record

    @staticmethod
    def save_verification_result(record, status, error=''):
        record.verification_status = status
        record.verification_error = str(error)
        record.date_verified = timezone.now()
        record.save(update_fields=[
            'verification_status', 'verification_error', 'date_verified',
        ])

    def get_runners(self):
        runners = super().get_runners()
        for account_id in sorted(
                self.account_ids - self.found_account_ids
        ):
            super().on_inventory_host_error(
                account_id, 'Account not found or inactive'
            )
            for key, record_id in self.recovery_record_map.items():
                if not key.endswith(f'-{account_id}'):
                    continue
                record = self.recovery_records.get(str(record_id))
                if record:
                    self.save_verification_result(
                        record,
                        ChangeSecretRecordStatusChoice.failed.value,
                        _('Account not found or inactive'),
                    )
        return runners

    def on_host_success(self, host, result):
        account = self.host_account_mapper.get(host)
        if not account:
            return super().on_host_error(
                host, 'Account mapping not found', result
            )
        record = self.host_record_mapper.get(host)
        if record:
            self.save_verification_result(
                record, ChangeSecretRecordStatusChoice.success.value
            )
            return super().on_host_success(host, result)
        try:
            account.set_connectivity(Connectivity.OK)
        except Exception as e:
            super().on_host_error(host, str(e), result)
            return
        super().on_host_success(host, result)

    def on_host_error(self, host, error, result):
        super().on_host_error(host, error, result)
        record = self.host_record_mapper.get(host)
        if record:
            self.save_verification_result(
                record,
                ChangeSecretRecordStatusChoice.failed.value,
                error,
            )
            return
        account = self.host_account_mapper.get(host)
        if not account:
            return
        try:
            error_tp = account.get_err_connectivity(error)
            account.set_connectivity(error_tp)
        except Exception as e:
            logger.warning(
                "Save account connectivity failure result failed: host=%s error=%s",
                host, e,
            )

    def post_run(self):
        try:
            if self.recovery_records:
                ChangeSecretRecord.objects.filter(
                    id__in=[
                        record.id
                        for record in self.recovery_records.values()
                    ],
                    verification_status=(
                        ChangeSecretRecordStatusChoice.pending.value
                    ),
                ).update(
                    verification_status=(
                        ChangeSecretRecordStatusChoice.unverified.value
                    ),
                    verification_error=str(_(
                        'Verification ended before a final result was received'
                    )),
                    date_verified=timezone.now(),
                )
        finally:
            super().post_run()
