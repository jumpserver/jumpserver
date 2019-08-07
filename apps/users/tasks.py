# -*- coding: utf-8 -*-
#

from celery import shared_task

from ops.celery.utils import create_or_update_celery_periodic_tasks
from ops.celery.decorator import after_app_ready_start
from common.utils import get_logger
from .models import User
from .utils import (
    send_password_expiration_reminder_mail, send_user_expiration_reminder_mail
)


logger = get_logger(__file__)


@shared_task
def check_password_expired():
    users = User.objects.exclude(role=User.ROLE_APP)
    for user in users:
        if not user.is_valid:
            continue
        if not user.password_will_expired:
            continue
        send_password_expiration_reminder_mail(user)
        msg = "The user {} password expires in {} days"
        logger.info(msg.format(user, user.password_expired_remain_days))


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


@shared_task
def check_user_expired():
    users = User.objects.exclude(role=User.ROLE_APP)
    for user in users:
        if not user.is_valid:
            continue
        if not user.will_expired:
            continue
        send_user_expiration_reminder_mail(user)


@shared_task
@after_app_ready_start
def check_user_expired_periodic():
    tasks = {
        'check_user_expired_periodic': {
            'task': check_user_expired.name,
            'interval': None,
            'crontab': '0 14 * * *',
            'enabled': True,
        }
    }
    create_or_update_celery_periodic_tasks(tasks)

