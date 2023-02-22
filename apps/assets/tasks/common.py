# -*- coding: utf-8 -*-
#
import uuid

from celery import current_task

from common.const.choices import Trigger
from orgs.utils import current_org


def generate_automation_execution_data(task_name, tp, task_snapshot=None):
    task_snapshot = task_snapshot or {}
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
    snapshot.update(task_snapshot)
    return {'id': eid, 'snapshot': snapshot}


def quickstart_automation(task_name, tp, task_snapshot=None):
    from assets.models import AutomationExecution
    data = generate_automation_execution_data(task_name, tp, task_snapshot)

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
