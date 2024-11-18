from accounts.const import AutomationTypes
from common.utils import get_logger
from ..base.manager import AccountBasePlaybookManager
from ..change_secret.manager import ChangeSecretManager

logger = get_logger(__name__)


class PushAccountManager(ChangeSecretManager, AccountBasePlaybookManager):
    @classmethod
    def method_type(cls):
        return AutomationTypes.push_account
