# -*- coding: utf-8 -*-
#
import datetime

from celery.utils.log import get_task_logger
from django.core.files.storage import default_storage
from django.utils import timezone
from celery import shared_task

from ops.celery.decorator import (
    register_as_period_task, after_app_shutdown_clean_periodic
)
from terminal.backends import server_replay_storage
from .models import UserLoginLog, OperateLog, FTPLog
from common.utils import get_log_keep_day
from .utils import find_ftplog_file_local

logger = get_task_logger(__name__)


@shared_task
@after_app_shutdown_clean_periodic
def clean_login_log_period():
    now = timezone.now()
    days = get_log_keep_day('LOGIN_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    UserLoginLog.objects.filter(datetime__lt=expired_day).delete()


@shared_task
@after_app_shutdown_clean_periodic
def clean_operation_log_period():
    now = timezone.now()
    days = get_log_keep_day('OPERATE_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    OperateLog.objects.filter(datetime__lt=expired_day).delete()


@shared_task
def clean_ftp_log_period():
    now = timezone.now()
    days = get_log_keep_day('FTP_LOG_KEEP_DAYS')
    expired_day = now - datetime.timedelta(days=days)
    OperateLog.objects.filter(datetime__lt=expired_day).delete()


@register_as_period_task(interval=3600*24)
@shared_task
def clean_audits_log_period():
    clean_login_log_period()
    clean_operation_log_period()
    clean_ftp_log_period()


@shared_task
def upload_ftp_log_file_to_external_storage(ftp_log_id, file_name):
    logger.info(f'Start upload session file record to external storage: {ftp_log_id} - {file_name}')
    ftp_log = FTPLog.objects.filter(id=ftp_log_id).first()
    if not ftp_log:
        logger.error(f'Session db item not found: {ftp_log_id}')
        return
    local_path, foobar = find_ftplog_file_local(ftp_log, file_name)
    if not local_path:
        logger.error(f'Session file record not found, may be upload error. file name: {file_name}')
        return
    abs_path = default_storage.path(local_path)
    remote_path = ftp_log.get_file_remote_path(file_name)
    ok, err = server_replay_storage.upload(abs_path, remote_path)
    if not ok:
        logger.error(f'Session file record upload to external error: {err}')
        return
    try:
        default_storage.delete(local_path)
    except:
        pass
    return
