from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from assets.automations.ping_gateway.manager import PingGatewayManager
from common.utils import get_logger

logger = get_logger(__name__)


class VerifyGatewayAccountManager(PingGatewayManager):

    @classmethod
    def method_type(cls):
        return AutomationTypes.verify_gateway_account

    @staticmethod
    def before_runner_start():
        logger.info(_(">>> Start executing the task to test gateway account connectivity"))

    def get_accounts(self, gateway):
        account_ids = self.execution.snapshot['accounts']
        accounts = gateway.accounts.filter(id__in=account_ids)
        return accounts
