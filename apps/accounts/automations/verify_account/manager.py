import os
from copy import deepcopy

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException

from accounts.const import (
    AutomationTypes, ChangeSecretRecordStatusChoice, Connectivity, SecretType,
)
from accounts.models import Account, ChangeSecretRecord, PersonalAssetCredential
from accounts.models.automations.verify_account import get_target_account_details
from accounts.personal_credentials import (
    get_personal_credential_permission_context,
    record_personal_credential_audit,
    validate_personal_credential_secret_type,
    validate_personal_credential_test_acl,
    validate_personal_credential_username,
    validate_personal_credential_verification_protocol,
)
from assets.automations.base.manager import BasePlaybookManager
from assets.automations.base.report import ConnectivityReportMixin
from common.const import Status
from common.utils import get_logger
from ops.ansible.utils import escape_jinja2_syntax, neutralize_jinja2_syntax
from users.models import User
from ..base.manager import AccountBasePlaybookManager

logger = get_logger(__name__)
UNAVAILABLE_ACCOUNT_ERROR = 'Account not found or inactive'


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
    def is_ds_account():
        # 个人凭据的用户名即登录用户名（目录服务账号已保存为 UPN），不再拼接域名
        return False

    @staticmethod
    def get_ansible_become_auth(path_dir=None):
        return {'ansible_become': False}

    def get_private_key_path(self, path):
        if self.secret_type != SecretType.SSH_KEY:
            return None
        return VerifyAccountManager.generate_private_key_path(
            self.secret, path
        )


class VerifyAccountManager(ConnectivityReportMixin, AccountBasePlaybookManager):

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

    def get_host_success_log(self, host):
        return BasePlaybookManager.get_host_success_log(self, host)

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
                validate_personal_credential_username(permission_account, credential.username)
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

    @staticmethod
    def format_inventory_host_label(host, detail):
        if isinstance(detail, dict):
            account = detail.get('account') or {}
            if account.get('full_username'):
                detail = {
                    **detail, 'account': {**account, 'username': account['full_username']},
                }
        return BasePlaybookManager.format_inventory_host_label(host, detail)

    def get_execution_account_label(self, detail):
        # Verification connects with the target credential, overriding the
        # privileged account initially selected for the asset inventory.
        account = detail.get('account') or {}
        protocol = (detail.get('jms_asset') or {}).get('protocol')
        username = account.get('username')
        if protocol in ('ssh', 'winrm', 'rdp'):
            username = account.get('full_username') or username
        auth = {}
        if protocol == 'ssh' and account.get('secret_type') == SecretType.PASSWORD:
            auth = dict(account.get('become') or {})
            # ssh_ping verifies passwords through su (or a network-device
            # enable method), regardless of the platform's sudo setting.
            if auth.get('ansible_become_method') not in ('enable', 'super', 'super_level'):
                auth['ansible_become_method'] = 'su'
        return self.format_execution_account_label(username, auth, account)

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
            full_username = account.full_username
            # Joined directory and local accounts can share a username on this asset.
            h['name'] += f'__account_{account_id}({neutralize_jinja2_syntax(full_username)})'
            self.host_account_mapper[h['name']] = account
            h['account'] = {
                'id': account_id,
                'username': escape_jinja2_syntax(account.username),
                'full_username': escape_jinja2_syntax(full_username),
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
            h['account'].update({
                'name': escape_jinja2_syntax(account.name),
                'privileged': account.privileged,
                'secret_type': account.secret_type,
                'secret': escape_jinja2_syntax(secret),
                'private_key_path': private_key_path,
                'become': account.get_ansible_become_auth(path_dir=path_dir),
            })
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

    def resolve_unavailable_account_details(self, account_ids, saved_details):
        snapshot_details = self.execution.snapshot.get('target_account_details', {})
        details = {}
        for account_id in account_ids:
            identity = snapshot_details.get(account_id) or saved_details.get(account_id)
            if identity and identity.get('username'):
                details[account_id] = identity

        missing_ids = account_ids - details.keys()
        if missing_ids:
            accounts = Account.objects.filter(
                id__in=missing_ids, org_id=self.execution.org_id,
            )
            details.update(get_target_account_details(accounts))
        return details

    @staticmethod
    def format_unavailable_account_label(account_id, details):
        identity = details.get(account_id, {})
        username = identity.get('username')
        if not username:
            return str(_(
                'Unable to resolve username (account ID: %(account_id)s)'
            ) % {'account_id': account_id})
        asset_name = identity.get('asset_name')
        return f'{asset_name} / {username}' if asset_name else username

    def get_report_failure_labels(self, result):
        account_ids = {
            str(target) for target, error in result.get('fail_assets', [])
            if error == UNAVAILABLE_ACCOUNT_ERROR and str(target) in self.account_ids
        }
        details = self.resolve_unavailable_account_details(
            account_ids, result.get('unavailable_account_details', {}),
        )
        return {
            account_id: self.format_unavailable_account_label(account_id, details)
            for account_id in account_ids
        }

    def get_runners(self):
        runners = super().get_runners()
        missing_account_ids = self.account_ids - self.found_account_ids
        details = self.resolve_unavailable_account_details(missing_account_ids, {})
        if details:
            self.result['unavailable_account_details'] = details
        for account_id in sorted(missing_account_ids):
            self.result.setdefault('account_details', {})[account_id] = {
                **details.get(account_id, {}), 'account_id': account_id,
            }
            self._inventory_host_labels[account_id] = self.format_unavailable_account_label(
                account_id, details,
            )
            super().on_inventory_host_error(account_id, UNAVAILABLE_ACCOUNT_ERROR)
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
        # Verification has no change/push record. Record its result directly
        # through the playbook manager instead of the secret-change callbacks.
        account = self.host_account_mapper.get(host)
        if not account:
            return BasePlaybookManager.on_host_error(
                self, host, 'Account mapping not found', result
            )
        record = self.host_record_mapper.get(host)
        if record:
            self.save_verification_result(
                record, ChangeSecretRecordStatusChoice.success.value
            )
            return BasePlaybookManager.on_host_success(self, host, result)
        if getattr(account, 'is_personal_credential', False):
            self.record_personal_credential_result(
                account, account.id, 'success'
            )
            return BasePlaybookManager.on_host_success(self, host, result)
        try:
            account.set_connectivity(Connectivity.OK)
        except Exception as e:
            BasePlaybookManager.on_host_error(self, host, str(e), result)
            return
        BasePlaybookManager.on_host_success(self, host, result)

    def on_host_error(self, host, error, result):
        BasePlaybookManager.on_host_error(self, host, error, result)
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
