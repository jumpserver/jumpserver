# -*- coding: utf-8 -*-
#

from celery import shared_task

from ops.celery.utils import (
    create_or_update_celery_periodic_tasks,
    after_app_ready_start
)
from .models import User
from common.utils import get_logger
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
