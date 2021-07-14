
from itertools import groupby
from collections import defaultdict

from celery import shared_task
from django.utils.translation import ugettext as _

from assets.models import Asset
from common.utils import get_logger
from orgs.utils import tmp_to_org, org_aware_func
from ..models import SystemUser, Connectivity, AuthBook
from . import const
from .utils import (
    clean_ansible_task_hosts, group_asset_by_platform
)

logger = get_logger(__name__)
__all__ = [
    'test_system_user_connectivity_util', 'test_system_user_connectivity_manual',
    'test_system_user_connectivity_period', 'test_system_user_connectivity_a_asset',
]


def set_assets_accounts_connectivity(system_user, assets, results_summary):
    asset_ids_ok = set()
    asset_ids_failed = set()

    asset_hostnames_ok = results_summary.get('contacted', {}).keys()

    for asset in assets:
        if asset.hostname in asset_hostnames_ok:
            asset_ids_ok.add(asset.id)
        else:
            asset_ids_failed.add(asset.id)

    accounts_ok = AuthBook.objects.filter(asset_id__in=asset_ids_ok, systemuser=system_user)
    accounts_failed = AuthBook.objects.filter(asset_id__in=asset_ids_failed, systemuser=system_user)

    AuthBook.bulk_set_connectivity(accounts_ok, Connectivity.ok)
    AuthBook.bulk_set_connectivity(accounts_failed, Connectivity.failed)


@org_aware_func("system_user")
def test_system_user_connectivity_util(system_user, assets, task_name):
    """
    Test system cant connect his assets or not.
    :param system_user:
    :param assets:
    :param task_name:
    :return:
    """
    from ops.utils import update_or_create_ansible_task

    if system_user.username_same_with_user:
        logger.error(_("Dynamic system user not support test"))
        return

    # hosts = clean_ansible_task_hosts(assets, system_user=system_user)
    # TODO: 这里不传递系统用户，因为clean_ansible_task_hosts会通过system_user来判断是否可以推送，
    # 不符合测试可连接性逻辑， 后面需要优化此逻辑
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

    def run_task(_tasks, _hosts, _username):
        old_name = "{}".format(system_user)
        new_name = "{}({})".format(system_user.name, _username)
        _task_name = task_name.replace(old_name, new_name)
        _task, created = update_or_create_ansible_task(
            task_name=_task_name, hosts=_hosts, tasks=_tasks,
            pattern='all', options=const.TASK_OPTIONS,
            run_as=_username, system_user=system_user
        )
        raw, summary = _task.run()
        success = summary.get('success', False)
        contacted = summary.get('contacted', {})
        dark = summary.get('dark', {})

        results_summary['success'] &= success
        results_summary['contacted'].update(contacted)
        results_summary['dark'].update(dark)

    for platform, _hosts in platform_hosts_map.items():
        if not _hosts:
            continue
        if platform not in ["unixlike", "windows"]:
            continue

        tasks = platform_tasks_map[platform]
        print(_("Start test system user connectivity for platform: [{}]").format(platform))
        print(_("Hosts count: {}").format(len(_hosts)))
        # 用户名不是动态的，用户名则是一个
        logger.debug("System user not has special auth")
        run_task(tasks, _hosts, system_user.username)

    set_assets_accounts_connectivity(system_user, hosts, results_summary)
    return results_summary


@shared_task(queue="ansible")
@org_aware_func("system_user")
def test_system_user_connectivity_manual(system_user, asset_ids=None):
    task_name = _("Test system user connectivity: {}").format(system_user)
    if asset_ids:
        assets = Asset.objects.filter(id__in=asset_ids)
    else:
        assets = system_user.get_related_assets()
    test_system_user_connectivity_util(system_user, assets, task_name)


@shared_task(queue="ansible")
@org_aware_func("system_user")
def test_system_user_connectivity_a_asset(system_user, asset):
    task_name = _("Test system user connectivity: {} => {}").format(
        system_user, asset
    )
    test_system_user_connectivity_util(system_user, [asset], task_name)


@shared_task(queue="ansible")
def test_system_user_connectivity_period():
    if not const.PERIOD_TASK_ENABLED:
        logger.debug("Period task disabled, test system user connectivity pass")
        return
    queryset_map = SystemUser.objects.all_group_by_org()
    for org, system_user in queryset_map.items():
        task_name = _("Test system user connectivity period: {}").format(system_user)
        with tmp_to_org(org):
            assets = system_user.get_related_assets()
            test_system_user_connectivity_util(system_user, assets, task_name)
