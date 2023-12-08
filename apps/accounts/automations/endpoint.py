from .backup_account.manager import AccountBackupManager
from .change_secret.manager import ChangeSecretManager
from .gather_accounts.manager import GatherAccountsManager
from .push_account.manager import PushAccountManager
from .remove_account.manager import RemoveAccountManager
from .verify_account.manager import VerifyAccountManager
from .verify_gateway_account.manager import VerifyGatewayAccountManager
from ..const import AutomationTypes


class ExecutionManager:
    manager_type_mapper = {
        AutomationTypes.push_account: PushAccountManager,
        AutomationTypes.change_secret: ChangeSecretManager,
        AutomationTypes.verify_account: VerifyAccountManager,
        AutomationTypes.remove_account: RemoveAccountManager,
        AutomationTypes.gather_accounts: GatherAccountsManager,
        AutomationTypes.verify_gateway_account: VerifyGatewayAccountManager,
        # TODO 后期迁移到自动化策略中
        'backup_account': AccountBackupManager,
    }

    def __init__(self, execution):
        self.execution = execution
        self._runner = self.manager_type_mapper[execution.manager_type](execution)

    def run(self, *args, **kwargs):
        return self._runner.run(*args, **kwargs)
