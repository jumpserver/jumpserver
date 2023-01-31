
import uuid

from assets.tasks.common import generate_data
from common.const.choices import Trigger


def automation_execute_start(task_name, tp, child_snapshot=None):
    from accounts.models import AutomationExecution
    data = generate_data(task_name, tp, child_snapshot)

    while True:
        try:
            _id = data['id']
            AutomationExecution.objects.get(id=_id)
            data['id'] = str(uuid.uuid4())
        except AutomationExecution.DoesNotExist:
            break
    execution = AutomationExecution.objects.create(
        trigger=Trigger.manual, **data
    )
    execution.start()
