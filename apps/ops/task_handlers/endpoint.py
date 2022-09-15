from ops.const import StrategyChoice
from .push import PushExecutionManager, PushHandler
from .verify import VerifyExecutionManager, VerifyHandler
from .collect import CollectExecutionManager, CollectHandler
from .change_auth import ChangeAuthExecutionManager, ChangeAuthHandler


class ExecutionManager:
    manager_type = {
        StrategyChoice.push: PushExecutionManager,
        StrategyChoice.verify: VerifyExecutionManager,
        StrategyChoice.collect: CollectExecutionManager,
        StrategyChoice.change_password: ChangeAuthExecutionManager,
    }

    def __new__(cls, execution):
        manager = cls.manager_type[execution.manager_type]
        return manager(execution)


class TaskHandler:
    handler_type = {
        StrategyChoice.push: PushHandler,
        StrategyChoice.verify: VerifyHandler,
        StrategyChoice.collect: CollectHandler,
        StrategyChoice.change_password: ChangeAuthHandler,
    }

    def __new__(cls, task, show_step_info):
        handler = cls.handler_type[task.handler_type]
        return handler(task, show_step_info)
