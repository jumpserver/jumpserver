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

from common.const.crontab import CRONTAB_AT_AM_TWO
from common.utils import get_log_keep_day, get_logger
from common.storage.ftp_file import FTPFileStorageHandler
from ops.celery.decorator import (
    register_as_period_task, after_app_shutdown_clean_periodic
)
from ops.models import CeleryTaskExecution
from terminal.models import Session, Command
from terminal.backends import server_replay_storage
from .models import UserLoginLog, OperateLog, FTPLog, ActivityLog, PasswordChangeLog

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


def clean_password_change_log_period():
    now = timezone.now()
    days = get_log_keep_day('PASSWORD_CHANGE_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    PasswordChangeLog.objects.filter(datetime__lt=expired_day).delete()
    logger.info("Clean password change log done")


def clean_activity_log_period():
    now = timezone.now()
    days = get_log_keep_day('ACTIVITY_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    ActivityLog.objects.filter(datetime__lt=expired_day).delete()


def clean_ftp_log_period():
    now = timezone.now()
    days = get_log_keep_day('FTP_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    file_store_dir = os.path.join(default_storage.base_location, 'ftp_file')
    FTPLog.objects.filter(date_start__lt=expired_day).delete()
    command = "find %s -mtime +%s -exec rm -f {} \\;" % (
        file_store_dir, days
    )
    subprocess.call(command, shell=True)
    command = "find %s -type d -empty -delete;" % file_store_dir
    subprocess.call(command, shell=True)
    logger.info("Clean FTP file done")


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
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
@after_app_shutdown_clean_periodic
def clean_audits_log_period():
    print("Start clean audit session task log")
    clean_login_log_period()
    clean_operation_log_period()
    clean_ftp_log_period()
    clean_activity_log_period()
    clean_celery_tasks_period()
    clean_expired_session_period()
    clean_password_change_log_period()


@shared_task(verbose_name=_('Upload FTP file to external storage'))
def upload_ftp_file_to_external_storage(ftp_log_id, file_name):
    logger.info(f'Start upload FTP file record to external storage: {ftp_log_id} - {file_name}')
    ftp_log = FTPLog.objects.filter(id=ftp_log_id).first()
    if not ftp_log:
        logger.error(f'FTP db item not found: {ftp_log_id}')
        return
    ftp_storage = FTPFileStorageHandler(ftp_log)
    local_path, url = ftp_storage.find_local()
    if not local_path:
        logger.error(f'FTP file record not found, may be upload error. file name: {file_name}')
        return
    abs_path = default_storage.path(local_path)
    ok, err = server_replay_storage.upload(abs_path, ftp_log.filepath)
    if not ok:
        logger.error(f'Session file record upload to external error: {err}')
        return
    try:
        default_storage.delete(local_path)
    except:
        pass
    return
