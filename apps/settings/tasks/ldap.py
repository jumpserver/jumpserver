# coding: utf-8
import time
from celery import shared_task
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from common.utils.timezone import local_now_display
from ops.celery.decorator import after_app_ready_start
from ops.celery.utils import (
    create_or_update_celery_periodic_tasks, disable_celery_periodic_task
)
from orgs.models import Organization
from settings.notifications import LDAPImportMessage
from users.models import User
from ..utils import LDAPSyncUtil, LDAPServerUtil, LDAPImportUtil

__all__ = [
    'sync_ldap_user', 'import_ldap_user_periodic', 'import_ldap_ha_user_periodic',
    'import_ldap_user', 'import_ldap_ha_user'
]

logger = get_logger(__file__)


def sync_ldap_user(category='ldap'):
    LDAPSyncUtil(category=category).perform_sync()


def perform_import(category, util_server):
    start_time = time.time()
    time_start_display = local_now_display()
    logger.info(f"Start import {category} ldap user task")

    util_import = LDAPImportUtil()
    users = util_server.search()

    if settings.XPACK_ENABLED:
        org_ids = getattr(settings, f"AUTH_{category.upper()}_SYNC_ORG_IDS")
        default_org = None
    else:
        org_ids = [Organization.DEFAULT_ID]
        default_org = Organization.default()

    orgs = list(set([Organization.get_instance(org_id, default=default_org) for org_id in org_ids]))
    new_users, errors = util_import.perform_import(users, orgs)

    if errors:
        logger.error(f"Imported {category} LDAP users errors: {errors}")
    else:
        logger.info(f"Imported {len(users)} {category} users successfully")

    receivers_setting = f"AUTH_{category.upper()}_SYNC_RECEIVERS"
    if getattr(settings, receivers_setting, None):
        user_ids = getattr(settings, receivers_setting)
        recipient_list = User.objects.filter(id__in=list(user_ids))
        end_time = time.time()
        extra_kwargs = {
            'orgs': orgs,
            'end_time': end_time,
            'start_time': start_time,
            'time_start_display': time_start_display,
            'new_users': new_users,
            'errors': errors,
            'cost_time': end_time - start_time,
        }
        for user in recipient_list:
            LDAPImportMessage(user, extra_kwargs).publish()


@shared_task(
    verbose_name=_('Periodic import ldap user'),
    description=_(
        """
        When LDAP auto-sync is configured, this task will be invoked to synchronize users
        """
    )
)
def import_ldap_user():
    perform_import('ldap', LDAPServerUtil())


@shared_task(
    verbose_name=_('Periodic import ldap ha user'),
    description=_(
        """
        When LDAP auto-sync is configured, this task will be invoked to synchronize users
        """
    )
)
def import_ldap_ha_user():
    perform_import('ldap_ha', LDAPServerUtil(category='ldap_ha'))


def register_periodic_task(task_name, task_func, interval_key, enabled_key, crontab_key, **kwargs):
    interval = kwargs.get(interval_key, settings.AUTH_LDAP_SYNC_INTERVAL)
    enabled = kwargs.get(enabled_key, settings.AUTH_LDAP_SYNC_IS_PERIODIC)
    crontab = kwargs.get(crontab_key, settings.AUTH_LDAP_SYNC_CRONTAB)

    if isinstance(interval, int):
        interval = interval * 3600
    else:
        interval = None

    if crontab:
        interval = None  # 优先使用 crontab

    tasks = {
        task_name: {
            'task': task_func.name,
            'interval': interval,
            'crontab': crontab,
            'enabled': enabled
        }
    }
    create_or_update_celery_periodic_tasks(tasks)


@shared_task(
    verbose_name=_('Registration periodic import ldap user task'),
    description=_(
        """
        When LDAP auto-sync parameters change, such as Crontab parameters, the LDAP sync task 
        will be re-registered or updated, and this task will be invoked
        """
    )
)
@after_app_ready_start
def import_ldap_user_periodic(**kwargs):
    register_periodic_task(
        'import_ldap_user_periodic', import_ldap_user,
        'AUTH_LDAP_SYNC_INTERVAL', 'AUTH_LDAP_SYNC_IS_PERIODIC',
        'AUTH_LDAP_SYNC_CRONTAB', **kwargs
    )


@shared_task(
    verbose_name=_('Registration periodic import ldap ha user task'),
    description=_(
        """
        When LDAP HA auto-sync parameters change, such as Crontab parameters, the LDAP HA sync task 
        will be re-registered or updated, and this task will be invoked
        """
    )
)
@after_app_ready_start
def import_ldap_ha_user_periodic(**kwargs):
    register_periodic_task(
        'import_ldap_ha_user_periodic', import_ldap_ha_user,
        'AUTH_LDAP_HA_SYNC_INTERVAL', 'AUTH_LDAP_HA_SYNC_IS_PERIODIC',
        'AUTH_LDAP_HA_SYNC_CRONTAB', **kwargs
    )
