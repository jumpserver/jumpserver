# ~*~ coding: utf-8 ~*~
from itertools import groupby
from collections import defaultdict
from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import get_logger
from orgs.utils import org_aware_func
from ..models.utils import Connectivity
from . import const
from .utils import clean_ansible_task_hosts, group_asset_by_platform


logger = get_logger(__file__)
__all__ = [
    'test_asset_connectivity_util', 'test_asset_connectivity_manual',
    'test_node_assets_connectivity_manual',
]


@shared_task(queue="ansible")
@org_aware_func("assets")
def test_asset_connectivity_util(assets, task_name=None):
    from ops.utils import update_or_create_ansible_task

    if task_name is None:
        task_name = _("Test assets connectivity")

    hosts = clean_ansible_task_hosts(assets)
    if not hosts:
        return {}
    platform_hosts_map = {}
    hosts_sorted = sorted(hosts, key=group_asset_by_platform)
    platform_hosts = groupby(hosts_sorted, key=group_asset_by_platform)
    for i in platform_hosts:
        platform_hosts_map[i[0]] = list(i[1])

    platform_tasks_map = {
        "unixlike": const.PING_UNIXLIKE_TASKS,
        "windows": const.PING_WINDOWS_TASKS
    }
    results_summary = dict(
        contacted=defaultdict(dict), dark=defaultdict(dict), success=True
    )
    for platform, _hosts in platform_hosts_map.items():
        if not _hosts:
            continue
        logger.debug("System user not has special auth")
        tasks = platform_tasks_map.get(platform)
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=_hosts, tasks=tasks,
            pattern='all', options=const.TASK_OPTIONS, run_as_admin=True,
        )
        raw, summary = task.run()
        success = summary.get('success', False)
        contacted = summary.get('contacted', {})
        dark = summary.get('dark', {})

        results_summary['success'] &= success
        results_summary['contacted'].update(contacted)
        results_summary['dark'].update(dark)
        continue

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


@shared_task(queue="ansible")
def test_node_assets_connectivity_manual(node):
    task_name = _("Test if the assets under the node are connectable: {}".format(node.name))
    assets = node.get_all_assets()
    result = test_asset_connectivity_util(assets, task_name=task_name)
    return result

