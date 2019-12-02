# -*- coding: utf-8 -*-
#
import datetime
from django.utils import timezone
from django.conf import settings
from celery import shared_task

from ops.celery.decorator import register_as_period_task
from .models import UserLoginLog, OperateLog
from .utils import write_login_log


@register_as_period_task(interval=3600*24)
@shared_task
def clean_login_log_period():
    now = timezone.now()
    try:
        days = int(settings.LOGIN_LOG_KEEP_DAYS)
    except ValueError:
        days = 90
    expired_day = now - datetime.timedelta(days=days)
    UserLoginLog.objects.filter(datetime__lt=expired_day).delete()


@register_as_period_task(interval=3600*24)
@shared_task
def clean_operation_log_period():
    now = timezone.now()
    try:
        days = int(settings.LOGIN_LOG_KEEP_DAYS)
    except ValueError:
        days = 90
    expired_day = now - datetime.timedelta(days=days)
    OperateLog.objects.filter(datetime__lt=expired_day).delete()


@shared_task
def write_login_log_async(*args, **kwargs):
    write_login_log(*args, **kwargs)
