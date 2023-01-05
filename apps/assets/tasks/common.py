# -*- coding: utf-8 -*-
#
import uuid
from celery import current_task
from orgs.utils import current_org

from common.const.choices import Trigger


def generate_data(task_name, tp, child_snapshot=None):
    child_snapshot = child_snapshot or {}
    from assets.models import BaseAutomation
    try:
        eid = current_task.request.id
    except AttributeError:
        eid = str(uuid.uuid4())

    data = {
        'type': tp,
        'name': task_name,
        'org_id': str(current_org.id)
    }

    automation_instance = BaseAutomation()
    snapshot = automation_instance.to_attr_json()
    snapshot.update(data)
    snapshot.update(child_snapshot)
    return {'id': eid, 'snapshot': snapshot}


def automation_execute_start(task_name, tp, child_snapshot=None):
    from assets.models import AutomationExecution
    data = generate_data(task_name, tp, child_snapshot)
    execution = AutomationExecution.objects.create(
        trigger=Trigger.manual, **data
    )
    execution.start()
