# coding: utf-8
import datetime

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from common.const.crontab import CRONTAB_AT_AM_TWO
from common.utils import get_logger, get_object_or_none, get_log_keep_day
from ops.celery import app
from orgs.utils import tmp_to_org, tmp_to_root_org
from .celery.decorator import (
    register_as_period_task, after_app_ready_start, after_app_shutdown_clean_periodic
)
from .celery.utils import (
    create_or_update_celery_periodic_tasks, get_celery_periodic_task,
    disable_celery_periodic_task, delete_celery_periodic_task
)
from .models import Job, JobExecution
from .notifications import ServerPerformanceCheckUtil

logger = get_logger(__file__)


def job_task_activity_callback(self, job_id, *args, **kwargs):
    job = get_object_or_none(Job, id=job_id)
    if not job:
        return
    resource_ids = [job.id]
    org_id = job.org_id
    return resource_ids, org_id


@shared_task(
    soft_time_limit=60, queue="ansible", verbose_name=_("Run ansible task"),
    activity_callback=job_task_activity_callback
)
def run_ops_job(job_id):
    with tmp_to_root_org():
        job = get_object_or_none(Job, id=job_id)
    if not job:
        logger.error("Did not get the execution: {}".format(job_id))
        return

    with tmp_to_org(job.org):
        execution = job.create_execution()
        execution.creator = job.creator
        run_ops_job_execution(execution.id)
        try:
            execution.start()
        except SoftTimeLimitExceeded:
            execution.set_error('Run timeout')
            logger.error("Run adhoc timeout")
        except Exception as e:
            execution.set_error(e)
            logger.error("Start adhoc execution error: {}".format(e))


def job_execution_task_activity_callback(self, execution_id, *args, **kwargs):
    execution = get_object_or_none(JobExecution, id=execution_id)
    if not execution:
        return
    resource_ids = [execution.id]
    org_id = execution.org_id
    return resource_ids, org_id


@shared_task(
    soft_time_limit=60, queue="ansible", verbose_name=_("Run ansible task execution"),
    activity_callback=job_execution_task_activity_callback
)
def run_ops_job_execution(execution_id, **kwargs):
    with tmp_to_root_org():
        execution = get_object_or_none(JobExecution, id=execution_id)

    if not execution:
        logger.error("Did not get the execution: {}".format(execution_id))
        return

    try:
        with tmp_to_org(execution.org):
            execution.start()
    except SoftTimeLimitExceeded:
        execution.set_error('Run timeout')
        logger.error("Run adhoc timeout")
    except Exception as e:
        execution.set_error(e)
        logger.error("Start adhoc execution error: {}".format(e))


@shared_task(verbose_name=_('Clear celery periodic tasks'))
@after_app_ready_start
def clean_celery_periodic_tasks():
    """清除celery定时任务"""
    logger.info('Start clean celery periodic tasks.')
    register_tasks = PeriodicTask.objects.all()
    for task in register_tasks:
        if task.task in app.tasks:
            continue

        task_name = task.name
        logger.info('Start clean task: {}'.format(task_name))
        disable_celery_periodic_task(task_name)
        delete_celery_periodic_task(task_name)
        task = get_celery_periodic_task(task_name)
        if task is None:
            logger.info('Clean task success: {}'.format(task_name))
        else:
            logger.info('Clean task failure: {}'.format(task))


@shared_task(verbose_name=_('Create or update periodic tasks'))
@after_app_ready_start
def create_or_update_registered_periodic_tasks():
    from .celery.decorator import get_register_period_tasks
    for task in get_register_period_tasks():
        create_or_update_celery_periodic_tasks(task)


@shared_task(verbose_name=_("Periodic check service performance"))
@register_as_period_task(interval=3600)
def check_server_performance_period():
    ServerPerformanceCheckUtil().check_and_publish()


@shared_task(verbose_name=_("Clean up unexpected jobs"))
@register_as_period_task(interval=3600)
def clean_up_unexpected_jobs():
    with tmp_to_root_org():
        JobExecution.clean_unexpected_execution()


@shared_task(verbose_name=_('Clean job_execution db record'))
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
@after_app_shutdown_clean_periodic
def clean_job_execution_period():
    logger.info("Start clean job_execution db record")
    now = timezone.now()
    days = get_log_keep_day('JOB_EXECUTION_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    with tmp_to_root_org():
        del_res = JobExecution.objects.filter(date_created__lt=expired_day).delete()
        logger.info(f"clean job_execution db record success! delete {days} days {del_res[0]} records")
