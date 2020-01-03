# coding: utf-8
import os
import subprocess
import time

from django.conf import settings
from celery import shared_task, subtask
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, get_object_or_none, get_disk_usage
from .celery.decorator import (
    register_as_period_task, after_app_shutdown_clean_periodic,
    after_app_ready_start
)
from .celery.utils import create_or_update_celery_periodic_tasks
from .models import Task, CommandExecution, CeleryTask
from .utils import send_server_performance_mail

logger = get_logger(__file__)


def rerun_task():
    pass


@shared_task(queue="ansible")
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


@shared_task(soft_time_limit=60, queue="ansible")
def run_command_execution(cid, **kwargs):
    execution = get_object_or_none(CommandExecution, id=cid)
    if execution:
        try:
            os.environ.update({
                "TERM_ROWS": kwargs.get("rows", ""),
                "TERM_COLS": kwargs.get("cols", ""),
            })
            execution.run()
        except SoftTimeLimitExceeded:
            logger.error("Run time out")
    else:
        logger.error("Not found the execution id: {}".format(cid))


@shared_task
@after_app_shutdown_clean_periodic
@register_as_period_task(interval=3600*24, description=_("Clean task history period"))
def clean_tasks_adhoc_period():
    logger.debug("Start clean task adhoc and run history")
    tasks = Task.objects.all()
    for task in tasks:
        adhoc = task.adhoc.all().order_by('-date_created')[5:]
        for ad in adhoc:
            ad.history.all().delete()
            ad.delete()


@shared_task
@after_app_shutdown_clean_periodic
@register_as_period_task(interval=3600*24, description=_("Clean celery log period"))
def clean_celery_tasks_period():
    expire_days = 30
    logger.debug("Start clean celery task history")
    one_month_ago = timezone.now() - timezone.timedelta(days=expire_days)
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
    command = "find %s -mtime +%s -name '*.log' -type f -exec rm -f {} \\;" % (
        settings.CELERY_LOG_DIR, expire_days
    )
    subprocess.call(command, shell=True)
    command = "echo > {}".format(os.path.join(settings.LOG_DIR, 'celery.log'))
    subprocess.call(command, shell=True)


@shared_task
@after_app_ready_start
def create_or_update_registered_periodic_tasks():
    from .celery.decorator import get_register_period_tasks
    for task in get_register_period_tasks():
        create_or_update_celery_periodic_tasks(task)


@shared_task
@register_as_period_task(interval=3600)
def check_server_performance_period():
    usages = get_disk_usage()
    usages = {path: usage for path, usage in usages.items()
              if not path.startswith('/etc')}

    for path, usage in usages.items():
        if usage.percent > 80:
            send_server_performance_mail(path, usage, usages)
            return


@shared_task(queue="ansible")
def hello(name, callback=None):
    import time
    time.sleep(10)
    print("Hello {}".format(name))


@shared_task
# @after_app_shutdown_clean_periodic
# @register_as_period_task(interval=30)
def hello123():
    return None


@shared_task
def hello_callback(result):
    print(result)
    print("Hello callback")


@shared_task
def add(a, b):
    time.sleep(5)
    return a + b


@shared_task
def add_m(x):
    from celery import chain
    a = range(x)
    b = [a[i:i + 10] for i in range(0, len(a), 10)]
    s = list()
    s.append(add.s(b[0], b[1]))
    for i in b[1:]:
        s.append(add.s(i))
    res = chain(*tuple(s))()
    return res
