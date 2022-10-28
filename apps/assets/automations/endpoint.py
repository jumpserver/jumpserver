from .change_secret.manager import ChangeSecretManager
from .gather_facts.manager import GatherFactsManager
from .gather_accounts.manager import GatherAccountsManager
from .verify_account.manager import VerifyAccountManager
from .push_account.manager import PushAccountManager
from ..const import AutomationTypes


class ExecutionManager:
    manager_type_mapper = {
        AutomationTypes.change_secret: ChangeSecretManager,
        AutomationTypes.gather_facts: GatherFactsManager,
        AutomationTypes.gather_accounts: GatherAccountsManager,
        AutomationTypes.verify_account: VerifyAccountManager,
        AutomationTypes.push_account: PushAccountManager,
    }

    def __init__(self, execution):
        self.execution = execution
        self._runner = self.manager_type_mapper[execution.manager_type](execution)

    def run(self, *args, **kwargs):
        return self._runner.run(*args, **kwargs)

