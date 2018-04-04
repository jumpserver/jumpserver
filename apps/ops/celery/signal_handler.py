# -*- coding: utf-8 -*-
#
import os
import datetime
import sys
import time

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from celery import subtask
from celery.signals import worker_ready, worker_shutdown, task_prerun, \
    task_postrun, after_task_publish
from django_celery_beat.models import PeriodicTask

from common.utils import get_logger, TeeObj, get_object_or_none
from common.const import celery_task_pre_key
from .utils import get_after_app_ready_tasks, get_after_app_shutdown_clean_tasks
from ..models import CeleryTask

logger = get_logger(__file__)


@worker_ready.connect
def on_app_ready(sender=None, headers=None, body=None, **kwargs):
    if cache.get("CELERY_APP_READY", 0) == 1:
        return
    cache.set("CELERY_APP_READY", 1, 10)
    logger.debug("App ready signal recv")
    tasks = get_after_app_ready_tasks()
    logger.debug("Start need start task: [{}]".format(
        ", ".join(tasks))
    )
    for task in tasks:
        subtask(task).delay()


@worker_shutdown.connect
def after_app_shutdown(sender=None, headers=None, body=None, **kwargs):
    if cache.get("CELERY_APP_SHUTDOWN", 0) == 1:
        return
    cache.set("CELERY_APP_SHUTDOWN", 1, 10)
    tasks = get_after_app_shutdown_clean_tasks()
    logger.debug("App shutdown signal recv")
    logger.debug("Clean need cleaned period tasks: [{}]".format(
        ', '.join(tasks))
    )
    PeriodicTask.objects.filter(name__in=tasks).delete()


@after_task_publish.connect
def after_task_publish_signal_handler(sender, headers=None, **kwargs):
    CeleryTask.objects.create(
        id=headers["id"], status=CeleryTask.WAITING, name=headers["task"]
    )
    cache.set(headers["id"], True, 3600)


@task_prerun.connect
def pre_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
    time.sleep(0.1)
    for i in range(5):
        if cache.get(task_id, False):
            break
        else:
            time.sleep(0.1)
            continue

    t = get_object_or_none(CeleryTask, id=task_id)
    if t is None:
        logger.warn("Not get the task: {}".format(task_id))
        return
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    log_path = os.path.join(now, task_id + '.log')
    full_path = os.path.join(CeleryTask.LOG_DIR, log_path)

    if not os.path.exists(os.path.dirname(full_path)):
        os.makedirs(os.path.dirname(full_path))
    with transaction.atomic():
        t.date_start = timezone.now()
        t.status = CeleryTask.RUNNING
        t.log_path = log_path
        t.save()
    f = open(full_path, 'w')
    tee = TeeObj(f)
    sys.stdout = tee
    task.log_f = tee


@task_postrun.connect
def post_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
    t = get_object_or_none(CeleryTask, id=task_id)
    if t is None:
        logger.warn("Not get the task: {}".format(task_id))
        return
    with transaction.atomic():
        t.status = CeleryTask.FINISHED
        t.date_finished = timezone.now()
        t.save()
    task.log_f.flush()
    sys.stdout = task.log_f.origin_stdout
    task.log_f.close()

