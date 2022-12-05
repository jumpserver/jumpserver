from common.utils import get_logger
from assets.const import AutomationTypes
from ..base.manager import BasePlaybookManager, PushOrVerifyHostCallbackMixin

logger = get_logger(__name__)


class PushAccountManager(PushOrVerifyHostCallbackMixin, BasePlaybookManager):
    need_privilege_account = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host_account_mapper = {}

    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account
