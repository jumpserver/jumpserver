from common.utils import get_logger
from accounts.const import AutomationTypes
from ..base.manager import PushOrVerifyHostCallbackMixin, AccountBasePlaybookManager

logger = get_logger(__name__)


class PushAccountManager(PushOrVerifyHostCallbackMixin, AccountBasePlaybookManager):
    need_privilege_account = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = {}

    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account
