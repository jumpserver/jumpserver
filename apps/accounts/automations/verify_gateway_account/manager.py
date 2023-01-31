from common.utils import get_logger
from accounts.const import AutomationTypes
from assets.automations.ping_gateway.manager import PingGatewayManager

logger = get_logger(__name__)


class VerifyGatewayAccountManager(PingGatewayManager):

    @classmethod
    def method_type(cls):
        return AutomationTypes.verify_gateway_account

    @staticmethod
    def before_runner_start():
        logger.info(">>> 开始执行测试网关账号可连接性任务")

    def get_accounts(self, gateway):
        usernames = self.execution.snapshot['accounts']
        accounts = gateway.accounts.filter(username__in=usernames)
        return accounts
