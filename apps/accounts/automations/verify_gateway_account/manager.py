from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from assets.automations.base.manager import print_automation_log
from assets.automations.ping_gateway.manager import PingGatewayManager


class VerifyGatewayAccountManager(PingGatewayManager):

    @classmethod
    def method_type(cls):
        return AutomationTypes.verify_gateway_account

    @staticmethod
    def before_runner_start():
        print_automation_log(
            _("Checking gateway account connectivity"), 'progress'
        )

    def get_accounts(self, gateway):
        account_ids = self.execution.snapshot['accounts']
        accounts = gateway.accounts.filter(id__in=account_ids)
        return accounts
