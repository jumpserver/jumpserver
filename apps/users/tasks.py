# -*- coding: utf-8 -*-
#

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from users.notifications import PasswordExpirationReminderMsg
from ops.celery.utils import (
    create_or_update_celery_periodic_tasks, disable_celery_periodic_task
)
from ops.celery.decorator import after_app_ready_start
from common.utils import get_logger
from orgs.models import Organization
from .models import User
from users.notifications import UserExpirationReminderMsg
from settings.utils import LDAPServerUtil, LDAPImportUtil


logger = get_logger(__file__)


@shared_task
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
    date_expired_lt = timezone.now() + timezone.timedelta(days=User.DATE_EXPIRED_WARNING_DAYS)
    users = User.get_nature_users()\
        .filter(source=User.Source.local)\
        .filter(date_expired__lt=date_expired_lt)

    for user in users:
        if not user.is_valid:
            continue
        if not user.will_expired:
            continue
        msg = "The user {} will expires in {} days"
        logger.info(msg.format(user, user.expired_remain_days))
        UserExpirationReminderMsg(user).publish_async()


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
    if settings.XPACK_ENABLED:
        org_id = settings.AUTH_LDAP_SYNC_ORG_ID
        default_org = None
    else:
        # 社区版默认导入Default组织
        org_id = Organization.DEFAULT_ID
        default_org = Organization.default()
    org = Organization.get_instance(org_id, default=default_org)
    errors = util_import.perform_import(users, org)
    if errors:
        logger.error("Imported LDAP users errors: {}".format(errors))
    else:
        logger.info('Imported {} users successfully'.format(len(users)))


@shared_task
@after_app_ready_start
def import_ldap_user_periodic():
    if not settings.AUTH_LDAP:
        return
    task_name = 'import_ldap_user_periodic'
    if not settings.AUTH_LDAP_SYNC_IS_PERIODIC:
        disable_celery_periodic_task(task_name)
        return

    interval = settings.AUTH_LDAP_SYNC_INTERVAL
    if isinstance(interval, int):
        interval = interval * 3600
    else:
        interval = None
    crontab = settings.AUTH_LDAP_SYNC_CRONTAB
    if crontab:
        # 优先使用 crontab
        interval = None
    tasks = {
        task_name: {
            'task': import_ldap_user.name,
            'interval': interval,
            'crontab': crontab,
            'enabled': True,
        }
    }
    create_or_update_celery_periodic_tasks(tasks)
