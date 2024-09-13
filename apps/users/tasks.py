# -*- coding: utf-8 -*-
#
import uuid
from datetime import timedelta

from celery import shared_task, current_task
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext_noop

from audits.const import ActivityChoices
from common.const.crontab import CRONTAB_AT_AM_TEN, CRONTAB_AT_PM_TWO
from common.utils import get_logger
from ops.celery.decorator import after_app_ready_start, register_as_period_task
from ops.celery.utils import create_or_update_celery_periodic_tasks
from orgs.utils import tmp_to_root_org
from users.notifications import PasswordExpirationReminderMsg
from users.notifications import UserExpirationReminderMsg
from .models import User

logger = get_logger(__file__)


@shared_task(
    verbose_name=_('Check password expired'),
    description=_(
        """Check every day at 10 AM whether the passwords of users in the system are expired, 
        and send a notification 5 days in advance"""
    )
)
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


@shared_task(
    verbose_name=_('Periodic check password expired'),
    description=_(
        """With version iterations, new tasks may be added, or task names and execution times may 
        be modified. Therefore, upon system startup, it is necessary to register or update the 
        parameters of the task that checks if passwords have expired"""
    )
)
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


@shared_task(
    verbose_name=_('Check user expired'),
    description=_(
        """Check every day at 2 p.m whether the users in the system are expired, and send a 
        notification 5 days in advance"""
    )
)
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


@shared_task(
    verbose_name=_('Periodic check user expired'),
    description=_(
        """With version iterations, new tasks may be added, or task names and execution times may 
        be modified. Therefore, upon system startup, it is necessary to register or update the 
        parameters of the task that checks if users have expired"""
    )
)
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


@shared_task(
    verbose_name=_('Check unused users'),
    description=_(
        """At 2 p.m. every day, according to the configuration in "System Settings - Security - 
        Auth security - Auto disable threshold" users who have not logged in or whose API keys 
        have not been used for a long time will be disabled"""
    )
)
@register_as_period_task(crontab=CRONTAB_AT_PM_TWO)
@tmp_to_root_org()
def check_unused_users():
    uncommon_users_ttl = settings.SECURITY_UNCOMMON_USERS_TTL
    if not uncommon_users_ttl:
        return

    uncommon_users_ttl = int(uncommon_users_ttl)
    if uncommon_users_ttl <= 0 or uncommon_users_ttl >= 999:
        return

    seconds_to_subtract = uncommon_users_ttl * 24 * 60 * 60
    t = timezone.now() - timedelta(seconds=seconds_to_subtract)
    last_login_q = Q(last_login__lte=t) | (Q(last_login__isnull=True) & Q(date_joined__lte=t))
    api_key_q = Q(date_api_key_last_used__lte=t) | (
            Q(date_api_key_last_used__isnull=True) & Q(date_joined__lte=t))

    users = User.objects \
        .filter(date_joined__lt=t) \
        .filter(is_active=True) \
        .filter(last_login_q) \
        .filter(api_key_q) \
        .exclude(username='admin')

    if not users:
        return

    print("Some users are not used for a long time, and they will be disabled.")
    resource_ids = []
    for user in users:
        resource_ids.append(user.id)
        print('  - {}'.format(user.name))

    users.update(is_active=False)
    from audits.signal_handlers import create_activities
    if current_task:
        task_id = current_task.request.id
    else:
        task_id = str(uuid.uuid4())
    detail = gettext_noop('The user has not logged in recently and has been disabled.')
    create_activities(resource_ids, detail, task_id, action=ActivityChoices.task, org_id='')
