# ~*~ coding: utf-8 ~*~

from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import encrypt_password, get_logger
from . import const
from .utils import clean_hosts_by_protocol, clean_hosts


logger = get_logger(__file__)
__all__ = [
    'push_system_user_util', 'push_system_user_to_assets',
    'push_system_user_to_assets_manual', 'push_system_user_a_asset_manual',
]


def get_push_linux_system_user_tasks(system_user):
    tasks = [
        {
            'name': 'Add user {}'.format(system_user.username),
            'action': {
                'module': 'user',
                'args': 'name={} shell={} state=present'.format(
                    system_user.username, system_user.shell,
                ),
            }
        },
        {
            'name': 'Add group {}'.format(system_user.username),
            'action': {
                'module': 'group',
                'args': 'name={} state=present'.format(
                    system_user.username,
                ),
            }
        },
        {
            'name': 'Check home dir exists',
            'action': {
                'module': 'stat',
                'args': 'path=/home/{}'.format(system_user.username)
            },
            'register': 'home_existed'
        },
        {
            'name': "Set home dir permission",
            'action': {
                'module': 'file',
                'args': "path=/home/{0} owner={0} group={0} mode=700".format(system_user.username)
            },
            'when': 'home_existed.stat.exists == true'
        }
    ]
    if system_user.password:
        tasks.append({
            'name': 'Set {} password'.format(system_user.username),
            'action': {
                'module': 'user',
                'args': 'name={} shell={} state=present password={}'.format(
                    system_user.username, system_user.shell,
                    encrypt_password(system_user.password, salt="K3mIlKK"),
                ),
            }
        })
    if system_user.public_key:
        tasks.append({
            'name': 'Set {} authorized key'.format(system_user.username),
            'action': {
                'module': 'authorized_key',
                'args': "user={} state=present key='{}'".format(
                    system_user.username, system_user.public_key
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
            'name': 'Set {} sudo setting'.format(system_user.username),
            'action': {
                'module': 'lineinfile',
                'args': "dest=/etc/sudoers state=present regexp='^{0} ALL=' "
                        "line='{0} ALL=(ALL) NOPASSWD: {1}' "
                        "validate='visudo -cf %s'".format(
                    system_user.username, sudo,
                )
            }
        })

    return tasks


def get_push_windows_system_user_tasks(system_user):
    tasks = []
    if not system_user.password:
        return tasks
    tasks.append({
        'name': 'Add user {}'.format(system_user.username),
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
                    ''.format(system_user.name,
                              system_user.username,
                              system_user.password),
        }
    })
    return tasks


def get_push_system_user_tasks(host, system_user):
    if host.is_unixlike():
        tasks = get_push_linux_system_user_tasks(system_user)
    elif host.is_windows():
        tasks = get_push_windows_system_user_tasks(system_user)
    else:
        msg = _(
            "The asset {} system platform {} does not "
            "support run Ansible tasks".format(host.hostname, host.platform)
        )
        logger.info(msg)
        tasks = []
    return tasks


@shared_task(queue="ansible")
def push_system_user_util(system_user, assets, task_name):
    from ops.utils import update_or_create_ansible_task
    if not system_user.is_need_push():
        msg = _("Push system user task skip, auto push not enable or "
                "protocol is not ssh or rdp: {}").format(system_user.name)
        logger.info(msg)
        return {}

    # Set root as system user is dangerous
    if system_user.username.lower() in ["root", "administrator"]:
        msg = _("For security, do not push user {}".format(system_user.username))
        logger.info(msg)
        return {}

    hosts = clean_hosts(assets)
    if not hosts:
        return {}

    hosts = clean_hosts_by_protocol(system_user, hosts)
    if not hosts:
        return {}

    for host in hosts:
        system_user.load_specific_asset_auth(host)
        tasks = get_push_system_user_tasks(host, system_user)
        if not tasks:
            continue
        task, created = update_or_create_ansible_task(
            task_name=task_name, hosts=[host], tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True,
            created_by=system_user.org_id,
        )
        task.run()


@shared_task(queue="ansible")
def push_system_user_to_assets_manual(system_user):
    assets = system_user.get_all_assets()
    task_name = _("Push system users to assets: {}").format(system_user.name)
    return push_system_user_util(system_user, assets, task_name=task_name)


@shared_task(queue="ansible")
def push_system_user_a_asset_manual(system_user, asset):
    task_name = _("Push system users to asset: {} => {}").format(
        system_user.name, asset
    )
    return push_system_user_util(system_user, [asset], task_name=task_name)


@shared_task(queue="ansible")
def push_system_user_to_assets(system_user, assets):
    task_name = _("Push system users to assets: {}").format(system_user.name)
    return push_system_user_util(system_user, assets, task_name)



# @shared_task
# @register_as_period_task(interval=3600)
# @after_app_ready_start
# @after_app_shutdown_clean_periodic
# def push_system_user_period():
#     for system_user in SystemUser.objects.all():
#         push_system_user_related_nodes(system_user)