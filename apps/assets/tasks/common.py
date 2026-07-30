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
        request = current_task.request
        eid = request.id
        worker_hostname = request.hostname
    except AttributeError:
        eid = None
        worker_hostname = None
    eid = str(eid or uuid.uuid4())

    data = {
        'type': tp,
        'name': task_name,
        'org_id': str(current_org.id)
    }

    automation_instance = BaseAutomation()
    snapshot = automation_instance.to_attr_json()
    snapshot.update(data)
    snapshot.update(task_snapshot)
    # A single Celery task may create several automation executions (for
    # example, one per organisation and secret type). Secondary executions
    # receive a different primary key, but still belong to this Celery task.
    snapshot['celery_task_id'] = eid
    if worker_hostname:
        snapshot['celery_worker_hostname'] = worker_hostname
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
        type=tp, trigger=Trigger.manual, **data
    )
    execution.start()
    return execution
