# coding: utf-8

from __future__ import absolute_import, unicode_literals

from celery import shared_task

from common.utils import get_logger
from .utils import run_AdHoc

logger = get_logger(__file__)


@shared_task
def rerun_task(task_id):
    from .models import Task
    record = Task.objects.get(uuid=task_id)
    assets = record.assets_json
    task_tuple = record.module_args
    pattern = record.pattern
    task_name = record.name
    return run_AdHoc(task_tuple, assets, pattern=pattern,
                     task_name=task_name, task_id=task_id)
