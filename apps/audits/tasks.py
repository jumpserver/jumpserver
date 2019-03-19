# -*- coding: utf-8 -*-
#
import datetime
from django.utils import timezone
from django.conf import settings
from celery import shared_task

from ops.celery.decorator import register_as_period_task
from .models import UserLoginLog


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
