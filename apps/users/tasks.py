# -*- coding: utf-8 -*-
#

import datetime
from django.utils import timezone
from django.conf import settings
from celery import shared_task

from ops.celery.utils import create_or_update_celery_periodic_tasks
from ops.celery.decorator import after_app_ready_start, register_as_period_task
from common.utils import get_logger
from .models import User
from .utils import send_password_expiration_reminder_mail


logger = get_logger(__file__)


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



