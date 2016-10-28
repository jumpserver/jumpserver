from __future__ import unicode_literals

from .tasks import get_asset_hardware_info
from celery.result import AsyncResult


def start_get_hardware_info(*assets):
    result = get_asset_hardware_info.delay(*assets)
    return result.id


def get_hardware_info(task_id):
    result = AsyncResult(task_id)
    if result.ready():
        return {"Completed": False, "data": result.get()}
    else:
        return {"Completed": True, "data": None}
