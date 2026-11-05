from django.utils.translation import gettext_lazy as _

from accounts.const import (
    AutomationTypes,
)
from common.utils import get_logger
from ..base.manager import BaseChangeSecretPushManager
from ...models import PushSecretRecord

logger = get_logger(__name__)


class PushAccountManager(BaseChangeSecretPushManager):

    @staticmethod
    def require_update_version(account, record):
        account.skip_history_when_saving = True
        return False

    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account

    def should_update_account_on_success(self, result):
        if not self.execution.snapshot.get('create_only'):
            return True
        tasks = (result or {}).get('ok', result or {})
        existing = any(
            task.get('res', {}).get('ansible_facts', {}).get('jms_account_existing') is True
            for task in tasks.values()
        )
        return not existing

    def get_secret(self, account):
        secret = account.secret
        if not secret and not account.follows_template:
            secret = super().get_secret(account)
        return secret

    def gen_account_inventory(self, account, asset, h, path_dir):
        create_only = self.execution.snapshot.get('create_only', False)
        if create_only and asset.platform.automation.push_account_method not in {
            'push_account_posix', 'push_account_aix', 'push_account_windows', 'push_account_local_windows',
        }:
            raise ValueError(_('This push method does not support create-only mode'))
        h['jms_create_only'] = bool(create_only)
        secret = self.get_secret(account)
        secret_type = account.secret_type
        if not secret:
            raise ValueError(_('Secret cannot be empty'))
        record = self.get_or_create_record(asset, account, h['name'])
        new_secret, private_key_path = self.handle_ssh_secret(secret_type, secret, path_dir)
        h = self.gen_inventory(h, account, new_secret, private_key_path, asset, path_dir)
        return h, record

    def get_or_create_record(self, asset, account, name):
        asset_account_id = f'{asset.id}-{account.id}'

        if asset_account_id in self.record_map:
            record_id = self.record_map[asset_account_id]
            record = PushSecretRecord.objects.filter(id=record_id).first()
            if not record:
                raise ValueError(_(
                    'Push secret record not found: %(record_id)s'
                ) % {'record_id': record_id})
        else:
            record = self.create_record(asset, account)

        self.name_record_mapper[name] = record
        return record

    def create_record(self, asset, account):
        record = PushSecretRecord.objects.create(
            asset=asset, account=account, execution=self.execution,
            comment=f'{account.username}@{asset.address}'
        )
        return record

    def print_summary(self):
        records = {
            str(record.id): record
            for record in self.name_record_mapper.values()
        }.values()
        success, failed, unverified = self.get_record_result_counts(records)
        # Inventory preparation can reject an account before a push record is
        # created. Include those failures in the final summary while avoiding
        # double-counting record failures already tracked by fail_accounts.
        failed = max(failed, self.summary.get('fail_accounts', 0))
        self.print_result_summary(
            success,
            failed,
            unverified,
            total=success + failed + unverified,
            include_unverified=True,
        )

    def get_report_template(self):
        return "accounts/push_account_report.html"
