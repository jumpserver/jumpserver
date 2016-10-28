from __future__ import unicode_literals

from .tasks import *
from celery.result import AsyncResult


def start_get_hardware_info(*assets):
    result = get_asset_hardware_info.delay(*assets)
    return result.id


def get_result(task_id):
    result = AsyncResult(task_id)
    if result.ready():
        return {"Completed": True, "data": result.get()}
    else:
        return {"Completed": False, "data": None}


def start_ping_test(*assets):
    result = asset_test_ping_check.delay(*assets)
    return result.id


