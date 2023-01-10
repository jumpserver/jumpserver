from .ping.manager import PingManager
from .ping_gateway.manager import PingGatewayManager
from .gather_facts.manager import GatherFactsManager
from ..const import AutomationTypes


class ExecutionManager:
    manager_type_mapper = {
        AutomationTypes.ping: PingManager,
        AutomationTypes.ping_gateway: PingGatewayManager,
        AutomationTypes.gather_facts: GatherFactsManager,
    }

    def __init__(self, execution):
        self.execution = execution
        self._runner = self.manager_type_mapper[execution.manager_type](execution)

    def run(self, *args, **kwargs):
        return self._runner.run(*args, **kwargs)
