# from .backup.manager import AccountBackupExecutionManager
#
#
from .change_password.manager import ChangePasswordManager


class ExecutionManager:
    manager_type_mapper = {
        'change_password': ChangePasswordManager,
    }

    def __init__(self, execution):
        self.execution = execution
        self._runner = self.manager_type_mapper[execution.automation.type](execution)

    def run(self, **kwargs):
        return self._runner.run(**kwargs)

