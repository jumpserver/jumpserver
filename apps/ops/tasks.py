# coding: utf-8
import os

from celery import shared_task, subtask
from django.utils import timezone

from common.utils import get_logger, get_object_or_none
from .celery.utils import register_as_period_task, after_app_shutdown_clean
from .models import Task, CommandExecution, CeleryTask

logger = get_logger(__file__)


def rerun_task():
    pass


@shared_task
def run_ansible_task(tid, callback=None, **kwargs):
    """
    :param tid: is the tasks serialized data
    :param callback: callback function name
    :return:
    """
    task = get_object_or_none(Task, id=tid)
    if task:
        result = task.run()
        if callback is not None:
            subtask(callback).delay(result, task_name=task.name)
        return result
    else:
        logger.error("No task found")


@shared_task
def run_command_execution(cid, **kwargs):
    execution = get_object_or_none(CommandExecution, id=cid)
    return execution.run()


@shared_task
@register_as_period_task(interval=3600*24)
@after_app_shutdown_clean
def clean_tasks_adhoc_period():
    logger.debug("Start clean task adhoc and run history")
    tasks = Task.objects.all()
    for task in tasks:
        adhoc = task.adhoc.all().order_by('-date_created')[5:]
        for ad in adhoc:
            ad.history.all().delete()
            ad.delete()


@shared_task
@register_as_period_task(interval=3600*24)
@after_app_shutdown_clean
def clean_celery_tasks_period():
    logger.debug("Start clean celery task history")
    one_month_ago = timezone.now() - timezone.timedelta(days=30)
    tasks = CeleryTask.objects.filter(date_start__lt=one_month_ago)
    for task in tasks:
        if os.path.isfile(task.full_log_path):
            try:
                os.remove(task.full_log_path)
            except (FileNotFoundError, PermissionError):
                pass
        task.delete()
    tasks = CeleryTask.objects.filter(date_start__isnull=True)
    tasks.delete()


@shared_task
def hello(name, callback=None):
    print("Hello {}".format(name))
    if callback is not None:
        subtask(callback).delay("Guahongwei")


@shared_task
def hello_callback(result):
    print(result)
    print("Hello callback")
