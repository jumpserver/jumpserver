from .backup.manager import AccountBackupExecutionManager


class ExecutionManager:
    manager_type = {
        'backup': AccountBackupExecutionManager
    }

    def __new__(cls, execution):
        return AccountBackupExecutionManager(execution)
