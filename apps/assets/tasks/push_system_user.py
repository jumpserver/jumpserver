# ~*~ coding: utf-8 ~*~

from itertools import groupby
from celery import shared_task
from common.db.utils import get_object_if_need, get_objects
from django.utils.translation import ugettext as _
from django.db.models import Empty

from common.utils import encrypt_password, get_logger
from assets.models import SystemUser, Asset, AuthBook
from orgs.utils import org_aware_func, tmp_to_root_org
from . import const
from .utils import clean_ansible_task_hosts, group_asset_by_platform


logger = get_logger(__file__)
__all__ = [
    'push_system_user_util', 'push_system_user_to_assets',
    'push_system_user_to_assets_manual', 'push_system_user_a_asset_manual',
]


def _split_by_comma(raw: str):
    try:
        return [i.strip() for i in raw.split(',')]
    except AttributeError:
        return []


def _dump_args(args: dict):
    return ' '.join([f'{k}={v}' for k, v in args.items() if v is not Empty])


def get_push_unixlike_system_user_tasks(system_user, username=None):
    if username is None:
        username = system_user.username
    password = system_user.password
    public_key = system_user.public_key
    comment = system_user.name

    groups = _split_by_comma(system_user.system_groups)

    if groups:
        groups = '"%s"' % ','.join(groups)

    add_user_args = {
        'name': username,
        'shell': system_user.shell or Empty,
        'state': 'present',
        'home': system_user.home or Empty,
        'groups': groups or Empty,
        'comment': comment
    }

    tasks = [
        {
            'name': 'Add user {}'.format(username),
            'action': {
                'module': 'user',
                'args': _dump_args(add_user_args),
            }
        },
        {
            'name': 'Add group {}'.format(username),
            'action': {
                'module': 'group',
                'args': 'name={} state=present'.format(username),
            }
        }
    ]
    if not system_user.home:
        tasks.extend([
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
        ])
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
    groups = {'Users', 'Remote Desktop Users'}
    if system_user.system_groups:
        groups.update(_split_by_comma(system_user.system_groups))
    groups = ','.join(groups)

    tasks = []
    if not password:
        logger.error("Error: no password found")
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
                    'groups="{}" '
                    'groups_action=add '
                    ''.format(username, username, password, groups),
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
    assets = clean_ansible_task_hosts(assets, system_user=system_user)
    if not assets:
        return {}

    assets_sorted = sorted(assets, key=group_asset_by_platform)
    platform_hosts = groupby(assets_sorted, key=group_asset_by_platform)

    def run_task(_tasks, _hosts):
        if not _tasks:
            return
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=_hosts, tasks=_tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True,
        )
        task.run()

    if system_user.username_same_with_user:
        if username is None:
            # 动态系统用户，但是没有指定 username
            usernames = list(system_user.users.all().values_list('username', flat=True).distinct())
        else:
            usernames = [username]
    else:
        # 非动态系统用户指定 username 无效
        assert username is None, 'Only Dynamic user can assign `username`'
        usernames = [system_user.username]

    for platform, _assets in platform_hosts:
        _assets = list(_assets)
        if not _assets:
            continue
        print(_("Start push system user for platform: [{}]").format(platform))
        print(_("Hosts count: {}").format(len(_assets)))

        id_asset_map = {_asset.id: _asset for _asset in _assets}
        assets_id = id_asset_map.keys()
        no_special_auth = []
        special_auth_set = set()

        auth_books = AuthBook.objects.filter(username__in=usernames, asset_id__in=assets_id)

        for auth_book in auth_books:
            special_auth_set.add((auth_book.username, auth_book.asset_id))

        for _username in usernames:
            no_special_assets = []
            for asset_id in assets_id:
                if (_username, asset_id) not in special_auth_set:
                    no_special_assets.append(id_asset_map[asset_id])
            if no_special_assets:
                no_special_auth.append((_username, no_special_assets))

        for _username, no_special_assets in no_special_auth:
            tasks = get_push_system_user_tasks(system_user, platform, username=_username)
            run_task(tasks, no_special_assets)

        for auth_book in auth_books:
            system_user._merge_auth(auth_book)
            tasks = get_push_system_user_tasks(system_user, platform, username=auth_book.username)
            asset = id_asset_map[auth_book.asset_id]
            run_task(tasks, [asset])


@shared_task(queue="ansible")
@tmp_to_root_org()
def push_system_user_to_assets_manual(system_user, username=None):
    """
    将系统用户推送到与它关联的所有资产上
    """
    system_user = get_object_if_need(SystemUser, system_user)
    assets = system_user.get_related_assets()
    task_name = _("Push system users to assets: {}").format(system_user.name)
    return push_system_user_util(system_user, assets, task_name=task_name, username=username)


@shared_task(queue="ansible")
@tmp_to_root_org()
def push_system_user_a_asset_manual(system_user, asset, username=None):
    """
    将系统用户推送到一个资产上
    """
    if username is None:
        username = system_user.username
    task_name = _("Push system users to asset: {}({}) => {}").format(
        system_user.name, username, asset
    )
    return push_system_user_util(system_user, [asset], task_name=task_name, username=username)


@shared_task(queue="ansible")
@tmp_to_root_org()
def push_system_user_to_assets(system_user_id, assets_id, username=None):
    """
    推送系统用户到指定的若干资产上
    """
    system_user = SystemUser.objects.get(id=system_user_id)
    assets = get_objects(Asset, assets_id)
    task_name = _("Push system users to assets: {}").format(system_user.name)

    return push_system_user_util(system_user, assets, task_name, username=username)

# @shared_task
# @register_as_period_task(interval=3600)
# @after_app_ready_start
# @after_app_shutdown_clean_periodic
# def push_system_user_period():
#     for system_user in SystemUser.objects.all():
#         push_system_user_related_nodes(system_user)
