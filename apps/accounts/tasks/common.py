# -*- coding: utf-8 -*-
#
from assets.tasks.common import generate_data
from common.const.choices import Trigger


def automation_execute_start(task_name, tp, child_snapshot=None):
    from accounts.models import AutomationExecution
    data = generate_data(task_name, tp, child_snapshot)
    execution = AutomationExecution.objects.create(
        trigger=Trigger.manual, **data
    )
    execution.start()
