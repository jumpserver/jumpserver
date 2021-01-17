# -*- coding: utf-8 -*-
#
import datetime
from django.utils import timezone
from celery import shared_task

from ops.celery.decorator import (
    register_as_period_task, after_app_shutdown_clean_periodic
)
from .models import UserLoginLog, OperateLog
from common.utils import get_log_keep_day


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
