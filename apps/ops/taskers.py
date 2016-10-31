from __future__ import unicode_literals

from .tasks import *

from .models import Tasker, AnsiblePlay, AnsibleTask, AnsibleHostResult
from uuid import uuid1
from celery.result import AsyncResult


def get_result(task_id):
    result = AsyncResult(task_id)
    if result.ready():
        return {"Completed": True, "data": result.get()}
    else:
        return {"Completed": False, "data": None}


def start_get_hardware_info(*assets):
    name = "Get host hardware information"
    uuid = "tasker-" + uuid1().hex
    get_asset_hardware_info.delay(name, uuid, *assets)
    return uuid


def __get_hardware_info(tasker_uuid):
    tasker = Tasker.objects.get(uuid=tasker_uuid)
    host_results = []

    for play in tasker.plays.all():
        for t in play.tasks.all():
            for h in t.host_results.all():
                host_results.append(h)

    return host_results


def get_hardware_info(tasker_uuid):
    try:
        return {"msg": None, "data": __get_hardware_info(tasker_uuid)}
    except Exception as e:
        return {"msg": "query data failed!, %s" % e.message, "data": None}


def start_ping_test(*assets):
    name = "Test host connection"
    uuid = "tasker-" + uuid1().hex
    asset_test_ping_check.delay(name, uuid, *assets)
    return uuid


def __get_ping_test(tasker_uuid):
    tasker = Tasker.objects.get(uuid=tasker_uuid)
    host_results = []

    for play in tasker.plays.all():
        for t in play.tasks.all():
            for h in t.host_results.all():
                host_results.append(h)

    return host_results


def get_ping_test(tasker_uuid):
    try:
        return {"msg": None, "data": __get_ping_test(tasker_uuid)}
    except Exception as e:
        return {"msg": "query data failed!, %s" % e.message, "data": None}

