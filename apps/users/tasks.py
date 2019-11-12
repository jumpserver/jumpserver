# -*- coding: utf-8 -*-
#

import sys
from celery import shared_task
from django.conf import settings

from ops.celery.utils import (
    create_or_update_celery_periodic_tasks, disable_celery_periodic_task
)
from ops.celery.decorator import after_app_ready_start
from common.utils import get_logger
from .models import User
from .utils import (
    send_password_expiration_reminder_mail, send_user_expiration_reminder_mail
)
from settings.utils import LDAPServerUtil, LDAPImportUtil


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
def import_ldap_user():
    logger.info("Start import ldap user task")
    util_server = LDAPServerUtil()
    util_import = LDAPImportUtil()
    users = util_server.search()
    errors = util_import.perform_import(users)
    if errors:
        logger.error("Imported LDAP users errors: {}".format(errors))
    else:
        logger.info('Imported {} users successfully'.format(len(users)))


@shared_task
@after_app_ready_start
def import_ldap_user_periodic():
    if not settings.AUTH_LDAP:
        return
    if not settings.AUTH_LDAP_SYNC_IS_PERIODIC:
        task_name = sys._getframe().f_code.co_name
        disable_celery_periodic_task(task_name)
        return

    interval = settings.AUTH_LDAP_SYNC_INTERVAL
    if isinstance(interval, int):
        interval = interval * 3600
    else:
        interval = None
    crontab = settings.AUTH_LDAP_SYNC_CRONTAB
    tasks = {
        'import_ldap_user_periodic': {
            'task': import_ldap_user.name,
            'interval': interval,
            'crontab': crontab,
            'enabled': True,
        }
    }
    create_or_update_celery_periodic_tasks(tasks)
