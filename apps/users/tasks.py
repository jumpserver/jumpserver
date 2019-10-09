# -*- coding: utf-8 -*-
#

from celery import shared_task
from django.conf import settings

from ops.celery.utils import create_or_update_celery_periodic_tasks
from ops.celery.decorator import after_app_ready_start
from common.utils import get_logger
from .models import User
from .utils import (
    send_password_expiration_reminder_mail, send_user_expiration_reminder_mail
)
from settings.utils import LDAPUtil


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


@shared_task
def sync_ldap_user():
    logger.info("Start sync ldap user periodic task")
    util = LDAPUtil()
    result = util.sync_users()
    logger.info("Result: {}".format(result))


@shared_task
@after_app_ready_start
def sync_ldap_user_periodic():
    if not settings.AUTH_LDAP:
        return
    if not settings.AUTH_LDAP_SYNC_IS_PERIODIC:
        return

    interval = settings.AUTH_LDAP_SYNC_INTERVAL
    if isinstance(interval, int):
        interval = interval * 3600
    else:
        interval = None
    crontab = settings.AUTH_LDAP_SYNC_CRONTAB

    tasks = {
        'sync_ldap_user_periodic': {
            'task': sync_ldap_user.name,
            'interval': interval,
            'crontab': crontab,
            'enabled': True,
        }
    }
    create_or_update_celery_periodic_tasks(tasks)
