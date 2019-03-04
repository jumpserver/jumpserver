# -*- coding: utf-8 -*-
#

import datetime
from django.utils import timezone
from django.conf import settings
from celery import shared_task

from ops.celery.utils import create_or_update_celery_periodic_tasks
from ops.celery.decorator import after_app_ready_start, register_as_period_task
from common.utils import get_logger
from .models import User, LoginLog
from .utils import write_login_log, send_password_expiration_reminder_mail


logger = get_logger(__file__)


@shared_task
def write_login_log_async(*args, **kwargs):
    write_login_log(*args, **kwargs)


@shared_task
def check_password_expired():
    users = User.objects.exclude(role=User.ROLE_APP)
    for user in users:
        if not user.password_will_expired:
            continue

        send_password_expiration_reminder_mail(user)
        logger.info("The user {} password expires in {} days".format(
            user, user.password_expired_remain_days)
        )


@shared_task
@after_app_ready_start
def check_password_expired_periodic():
    tasks = {
        'check_password_expired_periodic': {
            'task': check_password_expired.name,
            'interval': None,
            'crontab': '0 10 * * *',
            'enabled': True,
        }
    }
    create_or_update_celery_periodic_tasks(tasks)


@register_as_period_task(interval=3600*24)
@shared_task
def clean_login_log_period():
    now = timezone.now()
    try:
        days = int(settings.LOGIN_LOG_KEEP_DAYS)
    except ValueError:
        days = 90
    expired_day = now - datetime.timedelta(days=days)
    LoginLog.objects.filter(datetime__lt=expired_day).delete()
