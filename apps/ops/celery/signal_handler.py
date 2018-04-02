# -*- coding: utf-8 -*-
#
import os
import datetime
import sys

from django.conf import settings
from django.core.cache import cache
from celery import subtask
from celery.signals import worker_ready, worker_shutdown, task_prerun, \
    task_postrun, after_task_publish

from django_celery_beat.models import PeriodicTask

from common.utils import get_logger, TeeObj
from common.const import celery_task_pre_key

from .utils import get_after_app_ready_tasks, get_after_app_shutdown_clean_tasks


logger = get_logger(__file__)

WAITING = "waiting"
RUNNING = "running"
FINISHED = "finished"

EXPIRE_TIME = 3600


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


@task_prerun.connect
def pre_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
    task_key = celery_task_pre_key + task_id
    info = cache.get(task_key, {})
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    log_dir = os.path.join(settings.PROJECT_DIR, "data", "celery", now)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_path = os.path.join(log_dir, task_id + '.log')
    info.update({"status": RUNNING, "log_path": log_path})
    cache.set(task_key, info, EXPIRE_TIME)
    f = open(log_path, 'w')
    tee = TeeObj(f)
    sys.stdout = tee
    task.log_f = tee


@task_postrun.connect
def post_run_task_signal_handler(sender, task_id=None, task=None, **kwargs):
    task_key = celery_task_pre_key + task_id
    info = cache.get(task_key, {})
    info.update({"status": FINISHED})
    cache.set(task_key, info, EXPIRE_TIME)
    task.log_f.flush()
    sys.stdout = task.log_f.origin_stdout
    task.log_f.close()


@after_task_publish.connect
def after_task_publish_signal_handler(sender, headers=None, **kwargs):
    task_id = headers["id"]
    key = celery_task_pre_key + task_id
    cache.set(key, {"status": WAITING}, EXPIRE_TIME)