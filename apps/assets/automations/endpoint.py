# from .backup.manager import AccountBackupExecutionManager
#
#
from .change_secret.manager import ChangeSecretManager
from .gather_facts.manager import GatherFactsManager


class ExecutionManager:
    manager_type_mapper = {
        'change_secret': ChangeSecretManager,
        'gather_facts': GatherFactsManager,
    }

    def __init__(self, execution):
        self.execution = execution
        self._runner = self.manager_type_mapper[execution.manager_type](execution)

    def run(self, *args, **kwargs):
        return self._runner.run(*args, **kwargs)

