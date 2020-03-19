# ~*~ coding: utf-8 ~*~

from itertools import groupby
from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import encrypt_password, get_logger
from orgs.utils import tmp_to_org, org_aware_func
from . import const
from .utils import clean_ansible_task_hosts, group_asset_by_platform


logger = get_logger(__file__)
__all__ = [
    'push_system_user_util', 'push_system_user_to_assets',
    'push_system_user_to_assets_manual', 'push_system_user_a_asset_manual',
]


def get_push_unixlike_system_user_tasks(system_user, username=None):
    if username is None:
        username = system_user.username
    password = system_user.password
    public_key = system_user.public_key

    tasks = [
        {
            'name': 'Add user {}'.format(username),
            'action': {
                'module': 'user',
                'args': 'name={} shell={} state=present'.format(
                    username, system_user.shell or '/bin/bash',
                ),
            }
        },
        {
            'name': 'Add group {}'.format(username),
            'action': {
                'module': 'group',
                'args': 'name={} state=present'.format(username),
            }
        },
        {
            'name': 'Check home dir exists',
            'action': {
                'module': 'stat',
                'args': 'path=/home/{}'.format(username)
            },
            'register': 'home_existed'
        },
        {
            'name': "Set home dir permission",
            'action': {
                'module': 'file',
                'args': "path=/home/{0} owner={0} group={0} mode=700".format(username)
            },
            'when': 'home_existed.stat.exists == true'
        }
    ]
    if password:
        tasks.append({
            'name': 'Set {} password'.format(username),
            'action': {
                'module': 'user',
                'args': 'name={} shell={} state=present password={}'.format(
                    username, system_user.shell,
                    encrypt_password(password, salt="K3mIlKK"),
                ),
            }
        })
    if public_key:
        tasks.append({
            'name': 'Set {} authorized key'.format(username),
            'action': {
                'module': 'authorized_key',
                'args': "user={} state=present key='{}'".format(
                    username, public_key
                )
            }
        })
    if system_user.sudo:
        sudo = system_user.sudo.replace('\r\n', '\n').replace('\r', '\n')
        sudo_list = sudo.split('\n')
        sudo_tmp = []
        for s in sudo_list:
            sudo_tmp.append(s.strip(','))
        sudo = ','.join(sudo_tmp)
        tasks.append({
            'name': 'Set {} sudo setting'.format(username),
            'action': {
                'module': 'lineinfile',
                'args': "dest=/etc/sudoers state=present regexp='^{0} ALL=' "
                        "line='{0} ALL=(ALL) NOPASSWD: {1}' "
                        "validate='visudo -cf %s'".format(username, sudo)
            }
        })

    return tasks


def get_push_windows_system_user_tasks(system_user, username=None):
    if username is None:
        username = system_user.username
    password = system_user.password
    tasks = []
    if not password:
        return tasks
    task = {
        'name': 'Add user {}'.format(username),
        'action': {
            'module': 'win_user',
            'args': 'fullname={} '
                    'name={} '
                    'password={} '
                    'state=present '
                    'update_password=always '
                    'password_expired=no '
                    'password_never_expires=yes '
                    'groups="Users,Remote Desktop Users" '
                    'groups_action=add '
                    ''.format(username, username, password),
        }
    }
    tasks.append(task)
    return tasks


def get_push_system_user_tasks(system_user, platform="unixlike", username=None):
    """
    :param system_user:
    :param platform:
    :param username: 当动态时，近推送某个
    :return:
    """
    get_task_map = {
        "unixlike": get_push_unixlike_system_user_tasks,
        "windows": get_push_windows_system_user_tasks,
    }
    get_tasks = get_task_map.get(platform, get_push_unixlike_system_user_tasks)
    if not system_user.username_same_with_user:
        return get_tasks(system_user)
    tasks = []
    # 仅推送这个username
    if username is not None:
        tasks.extend(get_tasks(system_user, username))
        return tasks
    users = system_user.users.all().values_list('username', flat=True)
    print(_("System user is dynamic: {}").format(list(users)))
    for _username in users:
        tasks.extend(get_tasks(system_user, _username))
    return tasks


@org_aware_func("system_user")
def push_system_user_util(system_user, assets, task_name, username=None):
    from ops.utils import update_or_create_ansible_task
    hosts = clean_ansible_task_hosts(assets, system_user=system_user)
    if not hosts:
        return {}

    platform_hosts_map = {}
    hosts_sorted = sorted(hosts, key=group_asset_by_platform)
    platform_hosts = groupby(hosts_sorted, key=group_asset_by_platform)
    for i in platform_hosts:
        platform_hosts_map[i[0]] = list(i[1])

    def run_task(_tasks, _hosts):
        if not _tasks:
            return
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=_hosts, tasks=_tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True,
        )
        task.run()

    for platform, _hosts in platform_hosts_map.items():
        if not _hosts:
            continue
        print(_("Start push system user for platform: [{}]").format(platform))
        print(_("Hosts count: {}").format(len(_hosts)))

        if not system_user.has_special_auth():
            logger.debug("System user not has special auth")
            tasks = get_push_system_user_tasks(system_user, platform, username=username)
            run_task(tasks, _hosts)
            continue

        for _host in _hosts:
            system_user.load_asset_special_auth(_host)
            tasks = get_push_system_user_tasks(system_user, platform, username=username)
            run_task(tasks, [_host])


@shared_task(queue="ansible")
def push_system_user_to_assets_manual(system_user, username=None):
    assets = system_user.get_related_assets()
    task_name = _("Push system users to assets: {}").format(system_user.name)
    return push_system_user_util(system_user, assets, task_name=task_name, username=username)


@shared_task(queue="ansible")
def push_system_user_a_asset_manual(system_user, asset, username=None):
    if username is None:
        username = system_user.username
    task_name = _("Push system users to asset: {}({}) => {}").format(
        system_user.name, username, asset
    )
    return push_system_user_util(system_user, [asset], task_name=task_name, username=username)


@shared_task(queue="ansible")
def push_system_user_to_assets(system_user, assets, username=None):
    task_name = _("Push system users to assets: {}").format(system_user.name)
    return push_system_user_util(system_user, assets, task_name, username=username)



# @shared_task
# @register_as_period_task(interval=3600)
# @after_app_ready_start
# @after_app_shutdown_clean_periodic
# def push_system_user_period():
#     for system_user in SystemUser.objects.all():
#         push_system_user_related_nodes(system_user)
