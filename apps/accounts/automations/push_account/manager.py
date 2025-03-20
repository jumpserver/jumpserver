from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from common.utils import get_logger
from common.utils.timezone import local_now_filename
from ..base.manager import BaseChangeSecretPushManager
from ...models import PushSecretRecord

logger = get_logger(__name__)


class PushAccountManager(BaseChangeSecretPushManager):

    @staticmethod
    def require_update_version(account, recorder):
        account.skip_history_when_saving = True
        return False

    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account

    def get_secret(self, account):
        secret = account.secret
        if not secret:
            secret = super().get_secret(account)
        return secret

    def gen_account_inventory(self, account, asset, h, path_dir):
        secret = self.get_secret(account)
        secret_type = account.secret_type
        if not secret:
            raise ValueError(_('Secret cannot be empty'))
        self.get_or_create_record(asset, account, h['name'])
        new_secret, private_key_path = self.handle_ssh_secret(secret_type, secret, path_dir)
        h = self.gen_inventory(h, account, new_secret, private_key_path, asset)
        return h

    def get_or_create_record(self, asset, account, name):
        asset_account_id = f'{asset.id}-{account.id}'

        if asset_account_id in self.record_map:
            record_id = self.record_map[asset_account_id]
            recorder = PushSecretRecord.objects.filter(id=record_id).first()
        else:
            recorder = self.create_record(asset, account)

        self.name_recorder_mapper[name] = recorder
        return recorder

    def create_record(self, asset, account):
        recorder = PushSecretRecord(
            asset=asset, account=account, execution=self.execution,
            comment=f'{account.username}@{asset.address}'
        )
        return recorder

    def print_summary(self):
        print('\n\n' + '-' * 80)
        plan_execution_end = _('Plan execution end')
        print('{} {}\n'.format(plan_execution_end, local_now_filename()))
        time_cost = _('Duration')
        print('{}: {}s'.format(time_cost, self.duration))

    def get_report_template(self):
        return "accounts/push_account_report.html"
