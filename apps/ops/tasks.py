# coding: utf-8
import datetime
import os

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from django_celery_beat.models import PeriodicTask

from common.const.crontab import CRONTAB_AT_AM_TWO
from common.utils import get_logger, get_object_or_none, get_log_keep_day
from ops.celery import app
from ops.const import Types
from ops.serializers.job import JobExecutionSerializer
from orgs.utils import tmp_to_org, tmp_to_root_org
from .celery.decorator import (
    register_as_period_task, after_app_ready_start
)
from .celery.task_logging import TaskLog
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


def _run_ops_job_execution(execution):
    try:
        with tmp_to_org(execution.org):
            execution.start()
    except SoftTimeLimitExceeded:
        execution.set_error('Run timeout')
        logger.error("Run adhoc timeout")
    except Exception as e:
        execution.set_error(e)
        logger.error("Start adhoc execution error: {}".format(e))


@shared_task(
    soft_time_limit=60,
    queue="ansible",
    verbose_name=_("Run ansible task"),
    activity_callback=job_task_activity_callback,
    description=_(
        "Execute scheduled adhoc and playbooks, periodically invoking the task for execution"
    )
)
def run_ops_job(job_id):
    with tmp_to_root_org():
        job = get_object_or_none(Job, id=job_id)
    if not job:
        logger.error("Did not get the execution: {}".format(job_id))
        return
    if not settings.SECURITY_COMMAND_EXECUTION and job.type != Types.upload_file:
        return
    with tmp_to_org(job.org):
        execution = job.create_execution()
        execution.creator = job.creator
        if job.periodic_variable:
            execution.parameters = JobExecutionSerializer().validate_parameters(job.periodic_variable)
        try:
            execution.set_celery_id()
            execution.save()
            execution.check_login_asset_acls()
        except Exception as e:
            execution.set_error(e)
            logger.error("Start adhoc execution error: {}".format(e))
            return
        _run_ops_job_execution(execution)


def job_execution_task_activity_callback(self, execution_id, *args, **kwargs):
    execution = get_object_or_none(JobExecution, id=execution_id)
    if not execution:
        return
    resource_ids = [execution.id]
    org_id = execution.org_id
    return resource_ids, org_id


@shared_task(
    soft_time_limit=60,
    queue="ansible",
    verbose_name=_("Run ansible task execution"),
    activity_callback=job_execution_task_activity_callback,
    description=_(
        "Execute the task when manually adhoc or playbooks"
    )
)
def run_ops_job_execution(execution_id, **kwargs):
    with tmp_to_root_org():
        execution = get_object_or_none(JobExecution, id=execution_id)
    if not execution:
        logger.error("Did not get the execution: {}".format(execution_id))
        return
    if not settings.SECURITY_COMMAND_EXECUTION and execution.job.type != Types.upload_file:
        return
    _run_ops_job_execution(execution)


@shared_task(
    verbose_name=_('Clear celery periodic tasks'),
    description=_(
        "At system startup, clean up celery tasks that no longer exist"
    )
)
@after_app_ready_start
def clean_celery_periodic_tasks():
    """清除celery定时任务"""
    logger.info(gettext('Checking periodic tasks; tasks still registered in the worker will be kept.'))
    register_tasks = PeriodicTask.objects.all()
    checked = cleaned = kept = failed = 0
    for task in register_tasks:
        checked += 1
        if task.task in app.tasks:
            kept += 1
            continue

        task_name = task.name
        logger.info(gettext('Removing periodic task %(name)s: its task is no longer registered.'), {
            'name': task_name,
        })
        disable_celery_periodic_task(task_name)
        delete_celery_periodic_task(task_name)
        task = get_celery_periodic_task(task_name)
        if task is None:
            cleaned += 1
        else:
            failed += 1
            logger.warning(gettext('Periodic task %(name)s still exists after cleanup.'), {'name': task_name})
    logger.info(gettext(
        'Periodic tasks checked: %(checked)s; deleted: %(cleaned)s; '
        'kept because still registered: %(kept)s; cleanup failures: %(failed)s.'
    ), {'checked': checked, 'cleaned': cleaned, 'kept': kept, 'failed': failed})


@shared_task(
    verbose_name=_('Create or update periodic tasks'),
    description=_(
        """With version iterations, new tasks may be added, or task names and execution times may 
        be modified. Therefore, upon system startup, tasks will be registered or the parameters 
        of scheduled tasks will be updated"""
    )
)
@after_app_ready_start
def create_or_update_registered_periodic_tasks():
    from .celery.decorator import get_register_period_tasks
    logger.info(gettext('Starting periodic task registration.'))
    checked = created = updated = skipped = 0
    for task in get_register_period_tasks():
        checked += 1
        result = create_or_update_celery_periodic_tasks(task)
        if result is None:
            skipped += 1
        elif result[1]:
            created += 1
        else:
            updated += 1
    logger.info(gettext(
        'Periodic tasks checked: %(checked)s; created: %(created)s; '
        'updated: %(updated)s; skipped: %(skipped)s.'
    ), {'checked': checked, 'created': created, 'updated': updated, 'skipped': skipped})


@shared_task(
    verbose_name=_("Periodic check service performance"),
    description=_(
        """Check every hour whether each component is offline and whether the CPU, memory, 
        and disk usage exceed the thresholds, and send an alert message to the administrator"""
    )
)
@register_as_period_task(interval=300)
def check_server_performance_period():
    with TaskLog(logger, gettext('Periodic check service performance')) as log:
        if os.environ.get('SKIP_SERVER_PERFORMANCE_CHECK', False):
            log.skip(gettext('Service performance checks are disabled by configuration.'), 0)
            return
        checker = ServerPerformanceCheckUtil()
        checker.check()
        log.checked = len(checker._terminals) + checker.inactive_count
        log.processed = len(checker._terminals)
        if checker.inactive_count:
            log.skip(gettext('The component is inactive.'), checker.inactive_count)
        log.metric(gettext('Components with health alerts'), len(checker.terms_with_errors))
        checker.publish()
        if not checker.terms_with_errors:
            logger.info(gettext('No health alerts to send.'))


@shared_task(
    verbose_name=_("Clean up unexpected jobs"),
    description=_(
        """Due to exceptions caused by executing adhoc and playbooks in the Job Center, 
        which result in the task status not being updated, the system will clean up abnormal jobs 
        that have not been completed for more than 3 hours every hour and mark these tasks as 
        failed"""
    )
)
@register_as_period_task(interval=3600)
def clean_up_unexpected_jobs():
    logger.info(gettext('Checking running jobs; jobs older than %(hours)s hours will be marked failed.'), {
        'hours': 3,
    })
    with tmp_to_root_org():
        checked, cleaned = JobExecution.clean_unexpected_execution()
    logger.info(gettext(
        'Jobs checked: %(checked)s; marked failed: %(cleaned)s; '
        'skipped because within the time limit: %(skipped)s.'
    ), {'checked': checked, 'cleaned': cleaned, 'skipped': checked - cleaned})
    if not checked:
        logger.info(gettext('Nothing to process: no running jobs.'))


@shared_task(
    verbose_name=_('Clean job_execution db record'),
    description=_(
        """Due to the execution of adhoc and playbooks in the Job Center, execution records will 
        be generated. The system will clean up records that exceed the retention period every day 
        at 2 a.m., based on the configuration of 'System Settings - Tasks - Regular clean-up - 
        Job execution retention days'"""
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def clean_job_execution_period():
    now = timezone.now()
    days = get_log_keep_day('JOB_EXECUTION_KEEP_DAYS')
    logger.info(gettext('Checking job execution records older than %(days)s days.'), {'days': days})
    expired_day = now - datetime.timedelta(days=days)
    with tmp_to_root_org():
        expired = JobExecution.objects.filter(date_created__lt=expired_day)
        checked = expired.count()
        _, deleted = expired.delete()
    logger.info(gettext('Expired records matched: %(checked)s; deleted: %(deleted)s.'), {
        'checked': checked, 'deleted': deleted.get(JobExecution._meta.label, 0),
    })
    if not checked:
        logger.info(gettext('Nothing to clean: no records exceeded the retention period.'))

# 测试使用，注释隐藏
# @shared_task
# def longtime_add(x, y):
#     print('long time task begins')
#     time.sleep(50)
#     print('long time task finished')
#     return x + y
