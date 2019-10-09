# ~*~ coding: utf-8 ~*~

from celery import shared_task
from django.utils.translation import ugettext as _
from django.core.cache import cache

from common.utils import get_logger
from ops.celery.decorator import register_as_period_task

from ..models import AdminUser
from .utils import clean_hosts
from .asset_connectivity import test_asset_connectivity_util
from . import const


logger = get_logger(__file__)
__all__ = [
    'test_admin_user_connectivity_util', 'test_admin_user_connectivity_manual',
    'test_admin_user_connectivity_period'
]


@shared_task(queue="ansible")
def test_admin_user_connectivity_util(admin_user, task_name):
    """
    Test asset admin user can connect or not. Using ansible api do that
    :param admin_user:
    :param task_name:
    :return:
    """
    assets = admin_user.get_related_assets()
    hosts = clean_hosts(assets)
    if not hosts:
        return {}
    summary = test_asset_connectivity_util(hosts, task_name)
    return summary


@shared_task(queue="ansible")
@register_as_period_task(interval=3600)
def test_admin_user_connectivity_period():
    """
    A period task that update the ansible task period
    """
    if not const.PERIOD_TASK_ENABLED:
        logger.debug('Period task off, skip')
        return
    key = '_JMS_TEST_ADMIN_USER_CONNECTIVITY_PERIOD'
    prev_execute_time = cache.get(key)
    if prev_execute_time:
        logger.debug("Test admin user connectivity, less than 40 minutes, skip")
        return
    cache.set(key, 1, 60*40)
    admin_users = AdminUser.objects.all()
    for admin_user in admin_users:
        task_name = _("Test admin user connectivity period: {}").format(admin_user.name)
        test_admin_user_connectivity_util(admin_user, task_name)
    cache.set(key, 1, 60*40)


@shared_task(queue="ansible")
def test_admin_user_connectivity_manual(admin_user):
    task_name = _("Test admin user connectivity: {}").format(admin_user.name)
    test_admin_user_connectivity_util(admin_user, task_name)
    return True
