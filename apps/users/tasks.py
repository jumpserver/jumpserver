# -*- coding: utf-8 -*-
#
import uuid
from datetime import timedelta

from celery import shared_task, current_task
from django.conf import settings
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _, gettext_noop

from audits.const import ActivityChoices
from common.const.crontab import CRONTAB_AT_AM_TEN, CRONTAB_AT_PM_TWO
from common.utils import get_logger
from ops.celery.decorator import after_app_ready_start, register_as_period_task
from ops.celery.task_logging import TaskLog
from ops.celery.utils import create_or_update_celery_periodic_tasks
from orgs.utils import tmp_to_root_org
from users.notifications import PasswordExpirationReminderMsg
from users.notifications import UserExpirationReminderMsg
from .models import User

logger = get_logger(__file__)


def _iter_user_batches(users, batch_size=500):
    # SQL LIMIT bounds mysqlclient's buffered result as well as ORM instances.
    users = users.order_by('pk')
    last_pk = None
    while True:
        page = users if last_pk is None else users.filter(pk__gt=last_pk)
        batch = list(page[:batch_size])
        if not batch:
            break
        last_pk = batch[-1].pk
        yield batch
        if len(batch) < batch_size:
            break
        del batch


def _iter_password_expiration_users(batch_size=500):
    from rbac.builtin import BuiltinRole
    from rbac.const import Scope
    from rbac.models import OrgRoleBinding, SystemRoleBinding

    # Use the same scoped managers as User.is_org_admin, including root-org
    # behavior. Resolve the flag in SQL instead of creating role managers and
    # issuing role queries for every user.
    system_admins = SystemRoleBinding.objects.filter(
        user_id=OuterRef('pk'), role_id=BuiltinRole.system_admin.id,
        role__scope=Scope.system,
    )
    org_admins = OrgRoleBinding.objects.filter(
        user_id=OuterRef('pk'), role_id=BuiltinRole.org_admin.id,
        role__scope=Scope.org,
    )
    now = timezone.now()
    not_expired = Q()
    for is_admin, interval in (
        (True, settings.SECURITY_PASSWORD_EXPIRATION_TIME_ADMIN),
        (False, settings.SECURITY_PASSWORD_EXPIRATION_TIME),
    ):
        last_updated = now - timedelta(days=int(interval))
        not_expired |= Q(
            is_org_admin=is_admin,
            date_password_last_updated__gte=last_updated,
        )

    users = User.get_nature_users().filter(
        source=User.Source.local, is_active=True,
    ).annotate(
        is_org_admin=Exists(system_admins) | Exists(org_admins),
    ).filter(
        Q(date_expired__isnull=True) | Q(date_expired__gte=now),
        not_expired,
    ).only(
        'id', 'name', 'username', 'email', 'source', 'is_active',
        'date_expired', 'date_password_last_updated',
    )

    # Keep the live five-day upper bound in password_will_expired: a password
    # can enter that window while a large scan is running.
    for batch in _iter_user_batches(users, batch_size):
        yield from batch
        del batch


@shared_task(
    verbose_name=_('Check password expired'),
    description=_(
        """Check every day at 10 AM whether the passwords of users in the system are expired, 
        and send a notification 5 days in advance"""
    )
)
def check_password_expired():
    logger.info(gettext('Checking active local users with unexpired accounts and passwords.'))
    checked = notified = invalid = outside_window = 0
    for user in _iter_password_expiration_users():
        checked += 1
        if not user.is_valid:
            invalid += 1
            continue
        if not user.password_will_expired:
            outside_window += 1
            continue
        logger.info(gettext('Queuing a password expiration reminder for %(user)s: %(days)s days remaining.'), {
            'user': user, 'days': user.password_expired_remain_days,
        })

        PasswordExpirationReminderMsg(user).publish_async()
        notified += 1
    logger.info(gettext(
        'Users checked: %(checked)s; reminders queued: %(notified)s; '
        'skipped because inactive or expired: %(invalid)s; '
        'skipped because outside the reminder window: %(outside)s.'
    ), {'checked': checked, 'notified': notified, 'invalid': invalid, 'outside': outside_window})
    if not checked:
        logger.info(gettext('Nothing to process: no users matched the check criteria.'))


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
        notification in advance"""
    )
)
def check_user_expired():
    first_notice_days = settings.USER_EXPIRED_FIRST_NOTICE_DAYS
    daily_notice_days = settings.USER_EXPIRED_DAILY_NOTICE_DAYS
    today = timezone.localdate()
    now = timezone.now()
    date_expired_lt = now + timezone.timedelta(days=first_notice_days + 1)
    logger.info(gettext(
        'Checking active local users expiring within %(first)s days; '
        'remind %(first)s days before expiry and daily within %(daily)s days.'
    ), {'first': first_notice_days, 'daily': daily_notice_days})
    users = User.get_nature_users() \
        .filter(source=User.Source.local, is_active=True) \
        .filter(date_expired__gte=now, date_expired__lt=date_expired_lt) \
        .only('id', 'name', 'username', 'is_active', 'date_expired')

    checked = notified = invalid = outside_window = 0
    for batch in _iter_user_batches(users):
        for user in batch:
            checked += 1
            if not user.is_valid:
                invalid += 1
                continue
            date_expired = timezone.localtime(user.date_expired).date()
            remain_days = (date_expired - today).days
            should_notify = (
                remain_days == first_notice_days
                or 0 <= remain_days <= daily_notice_days
            )
            if not should_notify:
                outside_window += 1
                continue
            logger.info(gettext('Queuing an account expiration reminder for %(user)s: %(days)s days remaining.'), {
                'user': user, 'days': remain_days,
            })
            UserExpirationReminderMsg(user).publish_async()
            notified += 1
        del batch
    logger.info(gettext(
        'Users checked: %(checked)s; reminders queued: %(notified)s; '
        'skipped because inactive or expired: %(invalid)s; '
        'skipped because outside the reminder window: %(outside)s.'
    ), {'checked': checked, 'notified': notified, 'invalid': invalid, 'outside': outside_window})
    if not checked:
        logger.info(gettext('Nothing to process: no users matched the check criteria.'))


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
    with TaskLog(logger, gettext('Check unused users')) as log:
        uncommon_users_ttl = settings.SECURITY_UNCOMMON_USERS_TTL
        if not uncommon_users_ttl:
            log.skip(gettext('Automatic disabling of unused users is not enabled.'), 0)
            return

        uncommon_users_ttl = int(uncommon_users_ttl)
        if uncommon_users_ttl <= 0 or uncommon_users_ttl >= 999:
            log.skip(gettext('The unused-user threshold is outside the enabled range of 1–998 days.'), 0)
            return
        logger.info(gettext('Checking users with no login or API key use for %(days)s days; admin is excluded.'), {
            'days': uncommon_users_ttl,
        })

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

        from audits.models import ActivityLog
        from orgs.models import Organization
        if current_task:
            task_id = current_task.request.id
        else:
            task_id = str(uuid.uuid4())
        detail = gettext_noop('The user has not logged in recently and has been disabled.')
        users = users.using(users.select_for_update().db).order_by('pk')
        last_pk = None
        while True:
            page = users if last_pk is None else users.filter(pk__gt=last_pk)
            with transaction.atomic(using=users.db):
                # Lock and recheck eligibility before disabling, so a concurrent
                # login cannot leave the audit describing users we did not disable.
                batch = list(page.select_for_update().values_list('pk', 'name')[:500])
                if not batch:
                    break
                resource_ids = [pk for pk, _ in batch]
                disabled = users.filter(pk__in=resource_ids).update(is_active=False)
                # Write directly on this connection. The shared activity helper's
                # buffer can retain failed inserts after this batch is rolled back.
                ActivityLog.objects.using(users.db).bulk_create(
                    [ActivityLog(
                        resource_id=pk, detail=detail, detail_id=task_id,
                        type=ActivityChoices.task, org_id=Organization.ROOT_ID,
                    ) for pk in resource_ids],
                    batch_size=50, ignore_conflicts=True,
                )
            log.checked += len(batch)
            log.processed += disabled
            log.metric(gettext('Users disabled'), disabled)
            if len(batch) > disabled:
                log.skip(gettext('The record was already handled by another task.'), len(batch) - disabled)
            last_pk = batch[-1][0]
            if len(batch) < 500:
                break
            del batch, resource_ids
