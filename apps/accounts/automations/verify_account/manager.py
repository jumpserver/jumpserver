import os
from copy import deepcopy

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException

from accounts.const import (
    AutomationTypes, ChangeSecretRecordStatusChoice, Connectivity, SecretType,
)
from accounts.models import Account, ChangeSecretRecord, PersonalAssetCredential
from accounts.personal_credentials import (
    get_personal_credential_permission_context,
    record_personal_credential_audit,
    validate_personal_credential_secret_type,
    validate_personal_credential_test_acl,
    validate_personal_credential_verification_protocol,
)
from common.const import Status
from common.utils import get_logger
from users.models import User
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)


class PersonalCredentialAccount:
    """Account-shaped adapter used only by the existing verification runner."""

    is_personal_credential = True

    def __init__(self, credential):
        self.credential = credential

    def __getattr__(self, item):
        return getattr(self.credential, item)

    @property
    def name(self):
        return self.credential.username

    @property
    def full_username(self):
        username = self.credential.username
        if '@' in username or '\\' in username:
            return username
        if self.credential.protocol != 'rdp':
            return username
        rdp = self.credential.asset.platform.protocols.filter(
            name='rdp'
        ).first()
        ad_domain = (rdp.setting or {}).get('ad_domain') if rdp else ''
        return '{}@{}'.format(username, ad_domain) if ad_domain else username

    @property
    def platform(self):
        return self.credential.asset.platform

    @property
    def privileged(self):
        return False

    @property
    def su_from(self):
        return None

    @staticmethod
    def escape_jinja2_syntax(value):
        return Account.escape_jinja2_syntax(value)

    @staticmethod
    def get_ansible_become_auth():
        return {'ansible_become': False}

    def get_private_key_path(self, path):
        if self.secret_type != SecretType.SSH_KEY:
            return None
        return VerifyAccountManager.generate_private_key_path(
            self.secret, path
        )


class VerifyAccountManager(AccountBasePlaybookManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = {}
        self.account_ids = set(map(
            str, self.execution.snapshot.get('accounts', [])
        ))
        self.personal_credential_ids = set(map(
            str, self.execution.snapshot.get('personal_credentials', [])
        ))
        self.found_account_ids = set()
        self.found_personal_credential_ids = set()
        self.personal_credential_accounts = {}
        self.personal_credential_versions = {
            str(key): value
            for key, value in self.execution.snapshot.get(
                'personal_credential_versions', {}
            ).items()
        }
        self.finalized_personal_credential_ids = set()
        self.personal_credential_errors = {}
        self.personal_credential_user = User.objects.filter(
            id=self.execution.snapshot.get('personal_credential_owner_id')
        ).first()
        self.personal_credential_remote_addr = self.execution.snapshot.get(
            'personal_credential_remote_addr'
        )
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

    def get_target_summary(self):
        if not self.personal_credential_ids:
            return super().get_target_summary()
        return _(
            "Targets: %(credentials)s personal credential(s) on %(assets)s asset(s)"
        ) % {
            'credentials': len(self.personal_credential_ids),
            'assets': len(set(map(
                str, self.execution.snapshot.get('assets', [])
            ))),
        }

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
        if not self.personal_credential_ids or not self.personal_credential_user:
            return

        credentials = PersonalAssetCredential.objects.filter(
            id__in=self.personal_credential_ids,
            owner=self.personal_credential_user,
            is_active=True,
        ).select_related('asset__platform').defer('_secret')
        for credential in credentials:
            credential_id = str(credential.id)
            account = PersonalCredentialAccount(credential)
            self.personal_credential_accounts[credential_id] = account
            expected_version = self.personal_credential_versions.get(
                credential_id
            )
            if (
                    expected_version is not None
                    and credential.version != expected_version
            ):
                self.personal_credential_errors[credential_id] = (
                    'credential_changed_before_verification'
                )
                continue
            try:
                platform_protocol, permission_account = (
                    get_personal_credential_permission_context(
                        self.personal_credential_user,
                        credential.asset,
                        credential.protocol,
                    )
                )
                validate_personal_credential_secret_type(
                    platform_protocol, credential.secret_type
                )
                validate_personal_credential_test_acl(
                    self.personal_credential_user,
                    credential.asset,
                    permission_account,
                    credential.username,
                    self.personal_credential_remote_addr,
                )
                validate_personal_credential_verification_protocol(
                    credential.asset, credential.protocol
                )
            except APIException:
                self.personal_credential_errors[credential_id] = (
                    'permission_denied_or_credential_unavailable'
                )
                continue
            # Decrypt only after every dynamic permission/ACL check, and bind
            # the loaded secret to the exact version queued by the API.
            secret_version = (
                expected_version
                if expected_version is not None
                else credential.version
            )
            credential = PersonalAssetCredential.objects.filter(
                id=credential.id,
                owner=self.personal_credential_user,
                is_active=True,
                version=secret_version,
            ).select_related('asset__platform').first()
            if not credential:
                self.personal_credential_errors[credential_id] = (
                    'credential_changed_before_verification'
                )
                continue
            account = PersonalCredentialAccount(credential)
            self.personal_credential_accounts[credential_id] = account
            self._accounts_by_asset_id[str(credential.asset_id)].append(account)

    def get_inventory_account_selector(self):
        if not self.personal_credential_ids:
            return super().get_inventory_account_selector()
        return self.select_personal_inventory_account

    def select_personal_inventory_account(self, asset):
        accounts = self.get_accounts(asset)
        return next((
            account for account in accounts
            if getattr(account, 'is_personal_credential', False)
        ), None)

    def get_accounts(self, asset):
        self.load_accounts_by_asset()
        return self._accounts_by_asset_id.get(str(asset.id), [])

    def host_callback(self, host, asset=None, account=None, automation=None, path_dir=None, **kwargs):
        host = super().host_callback(
            host, asset=asset, account=account,
            automation=automation, path_dir=path_dir, **kwargs
        )
        if host.get('error'):
            if self.personal_credential_ids:
                self.load_accounts_by_asset()
                reasons = [
                    self.personal_credential_errors.get(credential_id)
                    for credential_id, personal_account
                    in self.personal_credential_accounts.items()
                    if (
                        str(personal_account.asset_id) == str(asset.id)
                        and self.personal_credential_errors.get(credential_id)
                    )
                ]
                if reasons:
                    host['error'] = reasons[0]
            return host

        accounts = self.get_accounts(asset)
        inventory_hosts = []

        for account in accounts:
            account_id = str(account.id)
            if getattr(account, 'is_personal_credential', False):
                self.found_personal_credential_ids.add(account_id)
            else:
                self.found_account_ids.add(account_id)
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
        missing_personal_ids = (
            self.personal_credential_ids
            - self.found_personal_credential_ids
        )
        if missing_personal_ids:
            self.status = Status.failed
        for credential_id in sorted(missing_personal_ids):
            reason = self.personal_credential_errors.get(
                credential_id, 'credential_not_found_or_not_permitted'
            )
            account = self.personal_credential_accounts.get(credential_id)
            self.record_personal_credential_result(
                account, credential_id, 'failed', reason
            )
        return runners

    def record_personal_credential_result(
            self, account, credential_id, result, failure_reason='',
    ):
        credential_id = str(credential_id)
        if credential_id in self.finalized_personal_credential_ids:
            return
        credential = account.credential if account else None
        if result != 'success':
            self.status = Status.failed
        connectivity = (
            Connectivity.OK if result == 'success' else Connectivity.ERR
        )
        expected_version = self.personal_credential_versions.get(
            credential_id
        )
        queryset = PersonalAssetCredential.objects.filter(
            id=credential_id,
            owner=self.personal_credential_user,
        )
        if expected_version is not None:
            queryset = queryset.filter(version=expected_version)
        updated = queryset.update(
            connectivity=connectivity,
            date_verified=timezone.now(),
        )
        if not updated:
            result = 'failed'
            failure_reason = 'credential_changed_during_verification'
            self.status = Status.failed
        # The connectivity result is final even when writing its audit record
        # fails. Do not let post_run turn a successful probe into a false
        # failure just to retry best-effort auditing.
        self.finalized_personal_credential_ids.add(credential_id)
        try:
            record_personal_credential_audit(
                operation='test',
                result=result,
                failure_reason=failure_reason,
                user=self.personal_credential_user,
                credential=credential,
                credential_id=credential_id,
                org_id=self.execution.org_id,
                remote_addr=self.personal_credential_remote_addr,
            )
        except Exception:
            logger.exception(
                'Record personal credential verification audit failed: %s',
                credential_id,
            )

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
        if getattr(account, 'is_personal_credential', False):
            self.record_personal_credential_result(
                account, account.id, 'success'
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
        if getattr(account, 'is_personal_credential', False):
            self.record_personal_credential_result(
                account,
                account.id,
                'failed',
                'credential_verification_failed',
            )
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
            for credential_id in (
                self.personal_credential_ids
                - self.finalized_personal_credential_ids
            ):
                account = self.personal_credential_accounts.get(credential_id)
                self.record_personal_credential_result(
                    account,
                    credential_id,
                    'failed',
                    'credential_verification_did_not_complete',
                )
        finally:
            super().post_run()
