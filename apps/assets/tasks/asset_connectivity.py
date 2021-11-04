# ~*~ coding: utf-8 ~*~
from itertools import groupby
from collections import defaultdict
from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import get_logger
from orgs.utils import org_aware_func
from ..models import Asset, Connectivity, AuthBook
from . import const
from .utils import (
    clean_ansible_task_hosts, group_asset_by_platform,
    CustomSSHClient, group_asset_by_auth_type, color_string
)


logger = get_logger(__file__)
__all__ = [
    'test_asset_connectivity_by_ansible', 'test_asset_connectivity_manual_by_ansible',
    'test_node_assets_connectivity_manual', 'test_assets_connectivity_manual',
    'test_asset_connectivity_by_ssh', 'test_asset_connectivity_manual_by_ssh',
    'test_assets_connectivity_manual'
]


def set_assets_accounts_connectivity(assets, results_summary):
    asset_ids_ok = set()
    asset_ids_failed = set()

    asset_hostnames_ok = results_summary.get('contacted', {}).keys()

    for asset in assets:
        if asset.hostname in asset_hostnames_ok:
            asset_ids_ok.add(asset.id)
        else:
            asset_ids_failed.add(asset.id)

    Asset.bulk_set_connectivity(asset_ids_ok, Connectivity.ok)
    Asset.bulk_set_connectivity(asset_ids_failed, Connectivity.failed)

    accounts_ok = AuthBook.objects.filter(asset_id__in=asset_ids_ok, systemuser__type='admin')
    accounts_failed = AuthBook.objects.filter(asset_id__in=asset_ids_failed, systemuser__type='admin')

    AuthBook.bulk_set_connectivity(accounts_ok, Connectivity.ok)
    AuthBook.bulk_set_connectivity(accounts_failed, Connectivity.failed)


@shared_task(queue="ansible")
@org_aware_func("assets")
def test_asset_connectivity_by_ansible(assets, task_name=None):
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
    set_assets_accounts_connectivity(assets, results_summary)
    return results_summary


@shared_task(queue="ansible")
def test_asset_connectivity_manual_by_ansible(asset):
    task_name = _("Test assets connectivity: {}").format(asset)
    summary = test_asset_connectivity_by_ansible([asset], task_name=task_name)

    if summary.get('dark'):
        return False, summary['dark']
    else:
        return True, ""


@shared_task(queue="ansible")
def test_assets_connectivity_manual(assets):
    task_name = _("Test assets connectivity: {}").format([asset.hostname for asset in assets])
    summary = test_asset_connectivity_by_ansible(assets, task_name=task_name)

    if summary.get('dark'):
        return False, summary['dark']
    else:
        return True, ""


@shared_task(queue="ansible")
def test_node_assets_connectivity_manual(node):
    assets = node.get_all_assets()
    custom_assets, ansible_assets = group_asset_by_auth_type(assets)

    task_name = '开始测试节点 {} 下自定义平台资产列表的可连接性'.format(node.name)
    results_summary = test_asset_connectivity_by_ssh(custom_assets, task_name=task_name)
    logger.info('Connectable: {}\nDark: {}'.format(
        color_string(results_summary['contacted'], 'green'),
        color_string(results_summary['dark'], 'red')
    ))

    if ansible_assets:
        task_name = _("Test if the assets under the node are connectable: {}".format(node.name))
        test_asset_connectivity_by_ansible(ansible_assets, task_name=task_name)


@shared_task
@org_aware_func("assets")
def test_asset_connectivity_by_ssh(assets, task_name=None):
    results_summary = dict(
        contacted=defaultdict(dict), dark=defaultdict(dict), success=True
    )

    if not assets:
        logger.info('没有匹配到自定义平台的资产')
        return results_summary

    if task_name is None:
        task_name = _("Test assets connectivity")
    logger.info(task_name)

    for asset in assets:
        contacted, dark = {}, {}
        connect_params = {
            'hostname': asset.ip,
            'port': asset.port,
            'username': asset.admin_user_username,
            'password': asset.admin_user_password,
            'allow_agent': False,
            'look_for_keys': False
        }
        ssh_client = CustomSSHClient()
        dark_msg = ssh_client.connect(**connect_params)
        ssh_client.close()
        if dark_msg:
            dark = {asset.hostname: dark_msg}
            success = False
        else:
            contacted = {asset.hostname: _('Connectable')}
            success = True

        results_summary['success'] &= success
        results_summary['contacted'].update(contacted)
        results_summary['dark'].update(dark)

    set_assets_accounts_connectivity(assets, results_summary)
    return results_summary


@shared_task
def test_asset_connectivity_manual_by_ssh(asset):
    summary = test_asset_connectivity_by_ssh([asset])

    if summary.get('dark'):
        return False, summary['dark']
    else:
        return True, ""


@shared_task(queue='ansible')
def test_assets_connectivity_manual(assets):
    custom_assets, ansible_assets = group_asset_by_auth_type(assets)

    if custom_assets:
        task_name = _("Test assets connectivity: {}").format([asset.hostname for asset in custom_assets])
        results_summary = test_asset_connectivity_by_ssh(custom_assets, task_name=task_name)
        logger.info('Connectable: {}\nDark: {}'.format(
            color_string(results_summary['contacted'], 'green'),
            color_string(results_summary['dark'], 'red')
        ))
    if ansible_assets:
        task_name = _("Test assets connectivity: {}").format([asset.hostname for asset in ansible_assets])
        test_asset_connectivity_by_ansible(ansible_assets, task_name=task_name)
