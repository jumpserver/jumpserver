# ~*~ coding: utf-8 ~*~

from itertools import groupby
from celery import shared_task
from common.db.utils import get_object_if_need, get_objects
from django.utils.translation import ugettext as _, gettext_noop
from django.db.models import Empty

from common.utils import encrypt_password, get_logger
from assets.models import SystemUser, Asset
from orgs.utils import org_aware_func, tmp_to_root_org
from . import const
from .utils import clean_ansible_task_hosts, group_asset_by_platform


logger = get_logger(__file__)
__all__ = [
    'push_system_user_util', 'push_system_user_to_assets',
    'push_system_user_to_assets_manual', 'push_system_user_a_asset_manual',
    'push_system_users_a_asset'
]


def _split_by_comma(raw: str):
    try:
        return [i.strip() for i in raw.split(',')]
    except AttributeError:
        return []


def _dump_args(args: dict):
    return ' '.join([f'{k}={v}' for k, v in args.items() if v is not Empty])


def get_push_unixlike_system_user_tasks(system_user, username=None, **kwargs):
    algorithm = kwargs.get('algorithm')
    if username is None:
        username = system_user.username

    comment = system_user.name
    if system_user.username_same_with_user:
        from users.models import User
        user = User.objects.filter(username=username).only('name', 'username').first()
        if user:
            comment = f'{system_user.name}[{str(user)}]'
    comment = comment.replace(' ', '')

    password = system_user.password
    public_key = system_user.public_key

    groups = _split_by_comma(system_user.system_groups)

    if groups:
        groups = '"%s"' % ','.join(groups)

    add_user_args = {
        'name': username,
        'shell': system_user.shell or Empty,
        'state': 'present',
        'home': system_user.home or Empty,
        'expires': -1,
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
                    encrypt_password(password, salt="K3mIlKK", algorithm=algorithm),
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


def get_push_windows_system_user_tasks(system_user: SystemUser, username=None, **kwargs):
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

    if system_user.ad_domain:
        logger.error('System user with AD domain do not support push.')
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


def get_push_system_user_tasks(system_user, platform="unixlike", username=None, algorithm=None):
    """
    获取推送系统用户的 ansible 命令，跟资产无关
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
        return get_tasks(system_user, algorithm=algorithm)
    tasks = []
    # 仅推送这个username
    if username is not None:
        tasks.extend(get_tasks(system_user, username, algorithm=algorithm))
        return tasks
    users = system_user.users.all().values_list('username', flat=True)
    print(_("System user is dynamic: {}").format(list(users)))
    for _username in users:
        tasks.extend(get_tasks(system_user, _username, algorithm=algorithm))
    return tasks


@org_aware_func("system_user")
def push_system_user_util(system_user, assets, task_name, username=None):
    from ops.utils import update_or_create_ansible_task
    assets = clean_ansible_task_hosts(assets, system_user=system_user)
    if not assets:
        return {}

    # 资产按平台分类
    assets_sorted = sorted(assets, key=group_asset_by_platform)
    platform_hosts = groupby(assets_sorted, key=group_asset_by_platform)

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

    def run_task(_tasks, _hosts):
        if not _tasks:
            return
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=_hosts, tasks=_tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True,
        )
        task.run()

    for platform, _assets in platform_hosts:
        _assets = list(_assets)
        if not _assets:
            continue
        print(_("Start push system user for platform: [{}]").format(platform))
        print(_("Hosts count: {}").format(len(_assets)))

        for u in usernames:
            for a in _assets:
                system_user.load_asset_special_auth(a, u)
                algorithm = 'des' if a.platform.name == 'AIX' else 'sha512'
                tasks = get_push_system_user_tasks(
                    system_user, platform, username=u,
                    algorithm=algorithm
                )
                run_task(tasks, [a])


@shared_task(queue="ansible")
@tmp_to_root_org()
def push_system_user_to_assets_manual(system_user, username=None):
    """
    将系统用户推送到与它关联的所有资产上
    """
    system_user = get_object_if_need(SystemUser, system_user)
    assets = system_user.get_related_assets()
    task_name = gettext_noop("Push system users to assets: ") + system_user.name
    return push_system_user_util(system_user, assets, task_name=task_name, username=username)


@shared_task(queue="ansible")
@tmp_to_root_org()
def push_system_user_a_asset_manual(system_user, asset, username=None):
    """
    将系统用户推送到一个资产上
    """
    # if username is None:
    #     username = system_user.username
    task_name = gettext_noop("Push system users to asset: ") + "{}({}) => {}".format(
        system_user.name, username or system_user.username, asset
    )
    return push_system_user_util(system_user, [asset], task_name=task_name, username=username)


@shared_task(queue="ansible")
@tmp_to_root_org()
def push_system_users_a_asset(system_users, asset):
    for system_user in system_users:
        push_system_user_a_asset_manual(system_user, asset)


@shared_task(queue="ansible")
@tmp_to_root_org()
def push_system_user_to_assets(system_user_id, asset_ids, username=None):
    """
    推送系统用户到指定的若干资产上
    """
    system_user = SystemUser.objects.get(id=system_user_id)
    assets = get_objects(Asset, asset_ids)
    task_name = gettext_noop("Push system users to assets: ") + system_user.name

    return push_system_user_util(system_user, assets, task_name, username=username)

# @shared_task
# @register_as_period_task(interval=3600)
# @after_app_ready_start
# @after_app_shutdown_clean_periodic
# def push_system_user_period():
#     for system_user in SystemUser.objects.all():
#         push_system_user_related_nodes(system_user)
