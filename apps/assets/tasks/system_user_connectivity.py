
from collections import defaultdict
from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import get_logger

from ..models import SystemUser
from . import const
from .utils import clean_hosts, clean_hosts_by_protocol

logger = get_logger(__name__)
__all__ = [
    'test_system_user_connectivity_util', 'test_system_user_connectivity_manual',
    'test_system_user_connectivity_period', 'test_system_user_connectivity_a_asset',
]


@shared_task(queue="ansible")
def test_system_user_connectivity_util(system_user, assets, task_name):
    """
    Test system cant connect his assets or not.
    :param system_user:
    :param assets:
    :param task_name:
    :return:
    """
    from ops.utils import update_or_create_ansible_task

    hosts = clean_hosts(assets)
    if not hosts:
        return {}

    hosts = clean_hosts_by_protocol(system_user, hosts)
    if not hosts:
        return {}

    hosts_category = {
        'linux': {
            'hosts': [],
            'tasks': const.TEST_SYSTEM_USER_CONN_TASKS
        },
        'windows': {
            'hosts': [],
            'tasks': const.TEST_WINDOWS_SYSTEM_USER_CONN_TASKS
        }
    }
    for host in hosts:
        hosts_list = hosts_category['windows']['hosts'] if host.is_windows() \
            else hosts_category['linux']['hosts']
        hosts_list.append(host)

    results_summary = dict(
        contacted=defaultdict(dict), dark=defaultdict(dict), success=True
    )
    for k, value in hosts_category.items():
        if not value['hosts']:
            continue
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=value['hosts'], tasks=value['tasks'],
            pattern='all', options=const.TASK_OPTIONS,
            run_as=system_user.username, created_by=system_user.org_id,
        )
        raw, summary = task.run()
        success = summary.get('success', False)
        contacted = summary.get('contacted', {})
        dark = summary.get('dark', {})

        results_summary['success'] &= success
        results_summary['contacted'].update(contacted)
        results_summary['dark'].update(dark)

    system_user.set_connectivity(results_summary)
    return results_summary


@shared_task(queue="ansible")
def test_system_user_connectivity_manual(system_user):
    task_name = _("Test system user connectivity: {}").format(system_user)
    assets = system_user.get_all_assets()
    return test_system_user_connectivity_util(system_user, assets, task_name)


@shared_task(queue="ansible")
def test_system_user_connectivity_a_asset(system_user, asset):
    task_name = _("Test system user connectivity: {} => {}").format(
        system_user, asset
    )
    return test_system_user_connectivity_util(system_user, [asset], task_name)


@shared_task(queue="ansible")
def test_system_user_connectivity_period():
    if not const.PERIOD_TASK_ENABLED:
        logger.debug("Period task disabled, test system user connectivity pass")
        return
    system_users = SystemUser.objects.all()
    for system_user in system_users:
        task_name = _("Test system user connectivity period: {}").format(system_user)
        assets = system_user.get_all_assets()
        test_system_user_connectivity_util(system_user, assets, task_name)
