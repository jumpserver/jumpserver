# -*- coding: utf-8 -*-
#
import datetime
import os
import subprocess

from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.utils import get_log_keep_day, get_logger
from ops.celery.decorator import (
    register_as_period_task, after_app_shutdown_clean_periodic
)
from ops.models import CeleryTaskExecution
from terminal.models import Session, Command
from .models import UserLoginLog, OperateLog, FTPLog, ActivityLog

logger = get_logger(__name__)


def clean_login_log_period():
    now = timezone.now()
    days = get_log_keep_day('LOGIN_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    UserLoginLog.objects.filter(datetime__lt=expired_day).delete()


def clean_operation_log_period():
    now = timezone.now()
    days = get_log_keep_day('OPERATE_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    OperateLog.objects.filter(datetime__lt=expired_day).delete()


def clean_activity_log_period():
    now = timezone.now()
    days = get_log_keep_day('ACTIVITY_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    ActivityLog.objects.filter(datetime__lt=expired_day).delete()


def clean_ftp_log_period():
    now = timezone.now()
    days = get_log_keep_day('FTP_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    FTPLog.objects.filter(date_start__lt=expired_day).delete()


def clean_celery_tasks_period():
    logger.debug("Start clean celery task history")
    expire_days = get_log_keep_day('TASK_LOG_KEEP_DAYS')
    days_ago = timezone.now() - timezone.timedelta(days=expire_days)
    tasks = CeleryTaskExecution.objects.filter(date_start__lt=days_ago)
    tasks.delete()
    tasks = CeleryTaskExecution.objects.filter(date_start__isnull=True)
    tasks.delete()
    command = "find %s -mtime +%s -name '*.log' -type f -exec rm -f {} \\;" % (
        settings.CELERY_LOG_DIR, expire_days
    )
    subprocess.call(command, shell=True)
    command = "echo > {}".format(os.path.join(settings.LOG_DIR, 'celery.log'))
    subprocess.call(command, shell=True)


def clean_expired_session_period():
    logger.info("Start clean expired session record, commands and replay")
    days = get_log_keep_day('TERMINAL_SESSION_KEEP_DURATION')
    expire_date = timezone.now() - timezone.timedelta(days=days)
    expired_sessions = Session.objects.filter(date_start__lt=expire_date)
    timestamp = expire_date.timestamp()
    expired_commands = Command.objects.filter(timestamp__lt=timestamp)
    replay_dir = os.path.join(default_storage.base_location, 'replay')

    expired_sessions.delete()
    logger.info("Clean session item done")
    expired_commands.delete()
    logger.info("Clean session command done")
    command = "find %s -mtime +%s \\( -name '*.json' -o -name '*.tar' -o -name '*.gz' \\) -exec rm -f {} \\;" % (
        replay_dir, days
    )
    subprocess.call(command, shell=True)
    command = "find %s -type d -empty -delete;" % replay_dir
    subprocess.call(command, shell=True)
    logger.info("Clean session replay done")


@shared_task(verbose_name=_('Clean audits session task log'))
@register_as_period_task(crontab='0 2 * * *')
@after_app_shutdown_clean_periodic
def clean_audits_log_period():
    print("Start clean audit session task log")
    clean_login_log_period()
    clean_operation_log_period()
    clean_ftp_log_period()
    clean_activity_log_period()
    clean_celery_tasks_period()
    clean_expired_session_period()
