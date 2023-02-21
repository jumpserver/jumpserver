import uuid

from assets.tasks.common import generate_automation_execution_data
from common.const.choices import Trigger


def quickstart_automation_by_snapshot(task_name, tp, task_snapshot=None):
    from accounts.models import AutomationExecution
    data = generate_automation_execution_data(task_name, tp, task_snapshot)

    pk = data['id']
    if AutomationExecution.objects.filter(id=pk).exists():
        data['id'] = str(uuid.uuid4())

    execution = AutomationExecution.objects.create(
        trigger=Trigger.manual, **data
    )
    execution.start()
