# ~*~ coding: utf-8 ~*~
from collections import defaultdict
from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import get_logger
from ..models.utils import Connectivity
from . import const
from .utils import clean_hosts


logger = get_logger(__file__)
__all__ = ['test_asset_connectivity_util', 'test_asset_connectivity_manual']


@shared_task(queue="ansible")
def test_asset_connectivity_util(assets, task_name=None):
    from ops.utils import update_or_create_ansible_task

    if task_name is None:
        task_name = _("Test assets connectivity")

    hosts = clean_hosts(assets)
    if not hosts:
        return {}

    hosts_category = {
        'linux': {
            'hosts': [],
            'tasks': const.TEST_ADMIN_USER_CONN_TASKS
        },
        'windows': {
            'hosts': [],
            'tasks': const.TEST_WINDOWS_ADMIN_USER_CONN_TASKS
        }
    }
    for host in hosts:
        hosts_list = hosts_category['windows']['hosts'] if host.is_windows() \
            else hosts_category['linux']['hosts']
        hosts_list.append(host)

    results_summary = dict(
        contacted=defaultdict(dict), dark=defaultdict(dict), success=True
    )
    created_by = assets[0].org_id
    for k, value in hosts_category.items():
        if not value['hosts']:
            continue
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=value['hosts'], tasks=value['tasks'],
            pattern='all', options=const.TASK_OPTIONS, run_as_admin=True,
            created_by=created_by,
        )
        raw, summary = task.run()
        success = summary.get('success', False)
        contacted = summary.get('contacted', {})
        dark = summary.get('dark', {})

        results_summary['success'] &= success
        results_summary['contacted'].update(contacted)
        results_summary['dark'].update(dark)

    for asset in assets:
        if asset.hostname in results_summary.get('dark', {}).keys():
            asset.connectivity = Connectivity.unreachable()
        elif asset.hostname in results_summary.get('contacted', {}).keys():
            asset.connectivity = Connectivity.reachable()
        else:
            asset.connectivity = Connectivity.unknown()
    return results_summary


@shared_task(queue="ansible")
def test_asset_connectivity_manual(asset):
    task_name = _("Test assets connectivity: {}").format(asset)
    summary = test_asset_connectivity_util([asset], task_name=task_name)

    if summary.get('dark'):
        return False, summary['dark']
    else:
        return True, ""
