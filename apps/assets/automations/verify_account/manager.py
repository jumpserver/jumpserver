from common.utils import get_logger
from assets.const import AutomationTypes, Connectivity
from ..base.manager import BasePlaybookManager, PushOrVerifyHostCallbackMixin

logger = get_logger(__name__)


class VerifyAccountManager(PushOrVerifyHostCallbackMixin, BasePlaybookManager):
    need_privilege_account = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = {}

    @classmethod
    def method_type(cls):
        return AutomationTypes.verify_account

    def on_host_success(self, host, result):
        account = self.host_account_mapper.get(host)
        account.set_connectivity(Connectivity.OK)

    def on_host_error(self, host, error, result):
        account = self.host_account_mapper.get(host)
        account.set_connectivity(Connectivity.FAILED)
