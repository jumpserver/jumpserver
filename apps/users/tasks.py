# -*- coding: utf-8 -*-
#

from celery import shared_task
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.const.crontab import CRONTAB_AT_AM_TEN, CRONTAB_AT_PM_TWO
from common.utils import get_logger
from ops.celery.decorator import after_app_ready_start
from ops.celery.utils import (
    create_or_update_celery_periodic_tasks
)
from users.notifications import PasswordExpirationReminderMsg
from users.notifications import UserExpirationReminderMsg
from .models import User

logger = get_logger(__file__)


@shared_task(verbose_name=_('Check password expired'))
def check_password_expired():
    users = User.get_nature_users().filter(source=User.Source.local)
    for user in users:
        if not user.is_valid:
            continue
        if not user.password_will_expired:
            continue
        msg = "The user {} password expires in {} days"
        logger.info(msg.format(user, user.password_expired_remain_days))

        PasswordExpirationReminderMsg(user).publish_async()


@shared_task(verbose_name=_('Periodic check password expired'))
@after_app_ready_start
def check_password_expired_periodic():
    tasks = {
        'check_password_expired_periodic': {
            'task': check_password_expired.name,
            'interval': None,
            'crontab': CRONTAB_AT_AM_TEN,
            'enabled': True,
        }
    }
    create_or_update_celery_periodic_tasks(tasks)


@shared_task(verbose_name=_('Check user expired'))
def check_user_expired():
    date_expired_lt = timezone.now() + timezone.timedelta(days=User.DATE_EXPIRED_WARNING_DAYS)
    users = User.get_nature_users() \
        .filter(source=User.Source.local) \
        .filter(date_expired__lt=date_expired_lt)

    for user in users:
        if not user.is_valid:
            continue
        if not user.will_expired:
            continue
        msg = "The user {} will expires in {} days"
        logger.info(msg.format(user, user.expired_remain_days))
        UserExpirationReminderMsg(user).publish_async()


@shared_task(verbose_name=_('Periodic check user expired'))
@after_app_ready_start
def check_user_expired_periodic():
    tasks = {
        'check_user_expired_periodic': {
            'task': check_user_expired.name,
            'interval': None,
            'crontab': CRONTAB_AT_PM_TWO,
            'enabled': True,
        }
    }
    create_or_update_celery_periodic_tasks(tasks)
