# ~*~ coding: utf-8 ~*~

import re
from collections import defaultdict
from celery import shared_task

from django.utils.translation import ugettext as _

from orgs.utils import tmp_to_org
from common.utils import get_logger
from ..models import GatheredUser, Node
from .utils import clean_hosts
from . import const

__all__ = ['gather_asset_users', 'gather_nodes_asset_users']
logger = get_logger(__name__)
space = re.compile('\s+')
ignore_login_shell = re.compile(r'nologin$|sync$|shutdown$|halt$')


def parse_linux_result_to_users(result):
    task_result = {}
    for task_name, raw in result.items():
        res = raw.get('ansible_facts', {}).get('getent_passwd')
        if res:
            task_result = res
            break
    if not task_result or not isinstance(task_result, dict):
        return []
    users = []
    for username, attr in task_result.items():
        if ignore_login_shell.search(attr[-1]):
            continue
        users.append(username)
    return users


def parse_windows_result_to_users(result):
    task_result = []
    for task_name, raw in result.items():
        res = raw.get('stdout_lines', {})
        if res:
            task_result = res
            break
    if not task_result:
        return []

    users = []

    for i in range(4):
        task_result.pop(0)
    for i in range(2):
        task_result.pop()

    for line in task_result:
        user = space.split(line)
        if user[0]:
            users.append(user[0])
    return users


def add_asset_users(assets, results):
    assets_map = {a.hostname: a for a in assets}
    parser_map = {
        'linux': parse_linux_result_to_users,
        'windows': parse_windows_result_to_users
    }

    assets_users_map = {}

    for platform, platform_results in results.items():
        for hostname, res in platform_results.items():
            parse = parser_map.get(platform)
            users = parse(res)
            logger.debug('Gathered host users: {} {}'.format(hostname, users))
            asset = assets_map.get(hostname)
            if not asset:
                continue
            assets_users_map[asset] = users

    for asset, users in assets_users_map.items():
        with tmp_to_org(asset.org_id):
            GatheredUser.objects.filter(asset=asset, present=True)\
                .update(present=False)
            for username in users:
                defaults = {'asset': asset, 'username': username, 'present': True}
                GatheredUser.objects.update_or_create(
                    defaults=defaults, asset=asset, username=username,
                )


@shared_task(queue="ansible")
def gather_asset_users(assets, task_name=None):
    from ops.utils import update_or_create_ansible_task
    if task_name is None:
        task_name = _("Gather assets users")
    assets = clean_hosts(assets)
    if not assets:
        return
    hosts_category = {
        'linux': {
            'hosts': [],
            'tasks': const.GATHER_ASSET_USERS_TASKS
        },
        'windows': {
            'hosts': [],
            'tasks': const.GATHER_ASSET_USERS_TASKS_WINDOWS
        }
    }
    for asset in assets:
        hosts_list = hosts_category['windows']['hosts'] if asset.is_windows() \
            else hosts_category['linux']['hosts']
        hosts_list.append(asset)

    results = {'linux': defaultdict(dict), 'windows': defaultdict(dict)}
    for k, value in hosts_category.items():
        if not value['hosts']:
            continue
        _task_name = '{}: {}'.format(task_name, k)
        task, created = update_or_create_ansible_task(
            task_name=_task_name, hosts=value['hosts'], tasks=value['tasks'],
            pattern='all', options=const.TASK_OPTIONS,
            run_as_admin=True, created_by=value['hosts'][0].org_id,
        )
        raw, summary = task.run()
        results[k].update(raw['ok'])
    add_asset_users(assets, results)


@shared_task(queue="ansible")
def gather_nodes_asset_users(nodes_key):
    assets = Node.get_nodes_all_assets(nodes_key)
    assets_groups_by_100 = [assets[i:i+100] for i in range(0, len(assets), 100)]
    for _assets in assets_groups_by_100:
        gather_asset_users(_assets)
