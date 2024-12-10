from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from common.utils import get_logger
from common.utils.timezone import local_now_filename
from ..base.manager import BaseChangeSecretPushManager

logger = get_logger(__name__)


class PushAccountManager(BaseChangeSecretPushManager):
    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account

    def get_secret(self, account):
        return account.secret

    def gen_account_inventory(self, account, asset, h, path_dir):
        secret = self.get_secret(account)
        secret_type = account.secret_type
        new_secret, private_key_path = self.handle_ssh_secret(secret_type, secret, path_dir)
        h = self.gen_inventory(h, account, new_secret, private_key_path, asset)
        return h

    def print_summary(self):
        print('\n\n' + '-' * 80)
        plan_execution_end = _('Plan execution end')
        print('{} {}\n'.format(plan_execution_end, local_now_filename()))
        time_cost = _('Duration')
        print('{}: {}s'.format(time_cost, self.duration))

    def get_report_template(self):
        return "accounts/push_account_report.html"
