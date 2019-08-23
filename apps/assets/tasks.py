# ~*~ coding: utf-8 ~*~
import json
import re
import os

from collections import defaultdict
from celery import shared_task
from django.utils.translation import ugettext as _
from django.core.cache import cache

from common.utils import (
    capacity_convert, sum_capacity, encrypt_password, get_logger
)
from ops.celery.decorator import (
    register_as_period_task, after_app_shutdown_clean_periodic
)

from .models import SystemUser, AdminUser
from .models.utils import Connectivity
from . import const


FORKS = 10
TIMEOUT = 60
logger = get_logger(__file__)
CACHE_MAX_TIME = 60*60*2
disk_pattern = re.compile(r'^hd|sd|xvd|vd')
PERIOD_TASK = os.environ.get("PERIOD_TASK", "on")


def check_asset_can_run_ansible(asset):
    if not asset.is_active:
        msg = _("Asset has been disabled, skipped: {}").format(asset)
        logger.info(msg)
        return False
    if not asset.is_support_ansible():
        msg = _("Asset may not be support ansible, skipped: {}").format(asset)
        logger.info(msg)
        return False
    return True


def clean_hosts(assets):
    clean_assets = []
    for asset in assets:
        if not check_asset_can_run_ansible(asset):
            continue
        clean_assets.append(asset)
    if not clean_assets:
        logger.info(_("No assets matched, stop task"))
    return clean_assets


def clean_hosts_by_protocol(system_user, assets):
    hosts = [
        asset for asset in assets
        if asset.has_protocol(system_user.protocol)
    ]
    if not hosts:
        msg = _("No assets matched related system user protocol, stop task")
        logger.info(msg)
    return hosts


@shared_task
def set_assets_hardware_info(assets, result, **kwargs):
    """
    Using ops task run result, to update asset info

    @shared_task must be exit, because we using it as a task callback, is must
    be a celery task also
    :param assets:
    :param result:
    :param kwargs: {task_name: ""}
    :return:
    """
    result_raw = result[0]
    assets_updated = []
    success_result = result_raw.get('ok', {})

    for asset in assets:
        hostname = asset.hostname
        info = success_result.get(hostname, {})
        info = info.get('setup', {}).get('ansible_facts', {})
        if not info:
            logger.error(_("Get asset info failed: {}").format(hostname))
            continue
        ___vendor = info.get('ansible_system_vendor', 'Unknown')
        ___model = info.get('ansible_product_name', 'Unknown')
        ___sn = info.get('ansible_product_serial', 'Unknown')

        for ___cpu_model in info.get('ansible_processor', []):
            if ___cpu_model.endswith('GHz') or ___cpu_model.startswith("Intel"):
                break
        else:
            ___cpu_model = 'Unknown'
        ___cpu_model = ___cpu_model[:48]
        ___cpu_count = info.get('ansible_processor_count', 0)
        ___cpu_cores = info.get('ansible_processor_cores', None) or \
                       len(info.get('ansible_processor', []))
        ___cpu_vcpus = info.get('ansible_processor_vcpus', 0)
        ___memory = '%s %s' % capacity_convert(
            '{} MB'.format(info.get('ansible_memtotal_mb'))
        )
        disk_info = {}
        for dev, dev_info in info.get('ansible_devices', {}).items():
            if disk_pattern.match(dev) and dev_info['removable'] == '0':
                disk_info[dev] = dev_info['size']
        ___disk_total = '%s %s' % sum_capacity(disk_info.values())
        ___disk_info = json.dumps(disk_info)

        # ___platform = info.get('ansible_system', 'Unknown')
        ___os = info.get('ansible_distribution', 'Unknown')
        ___os_version = info.get('ansible_distribution_version', 'Unknown')
        ___os_arch = info.get('ansible_architecture', 'Unknown')
        ___hostname_raw = info.get('ansible_hostname', 'Unknown')

        for k, v in locals().items():
            if k.startswith('___'):
                setattr(asset, k.strip('_'), v)
        asset.save()
        assets_updated.append(asset)
    return assets_updated


@shared_task
def update_assets_hardware_info_util(assets, task_name=None):
    """
    Using ansible api to update asset hardware info
    :param assets:  asset seq
    :param task_name: task_name running
    :return: result summary ['contacted': {}, 'dark': {}]
    """
    from ops.utils import update_or_create_ansible_task
    if task_name is None:
        task_name = _("Update some assets hardware info")
    tasks = const.UPDATE_ASSETS_HARDWARE_TASKS
    hosts = clean_hosts(assets)
    if not hosts:
        return {}
    created_by = str(assets[0].org_id)
    task, created = update_or_create_ansible_task(
        task_name, hosts=hosts, tasks=tasks, created_by=created_by,
        pattern='all', options=const.TASK_OPTIONS, run_as_admin=True,
    )
    result = task.run()
    set_assets_hardware_info(assets, result)
    return result


@shared_task
def update_asset_hardware_info_manual(asset):
    task_name = _("Update asset hardware info: {}").format(asset.hostname)
    update_assets_hardware_info_util(
        [asset], task_name=task_name
    )


@shared_task
def update_assets_hardware_info_period():
    """
    Update asset hardware period task
    :return:
    """
    if PERIOD_TASK != "on":
        logger.debug("Period task disabled, update assets hardware info pass")
        return


##  ADMIN USER CONNECTIVE  ##


@shared_task
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


@shared_task
def test_asset_connectivity_manual(asset):
    task_name = _("Test assets connectivity: {}").format(asset)
    summary = test_asset_connectivity_util([asset], task_name=task_name)

    if summary.get('dark'):
        return False, summary['dark']
    else:
        return True, ""


@shared_task
def test_admin_user_connectivity_util(admin_user, task_name):
    """
    Test asset admin user can connect or not. Using ansible api do that
    :param admin_user:
    :param task_name:
    :return:
    """
    assets = admin_user.get_related_assets()
    hosts = clean_hosts(assets)
    if not hosts:
        return {}
    summary = test_asset_connectivity_util(hosts, task_name)
    return summary


@shared_task
@register_as_period_task(interval=3600)
def test_admin_user_connectivity_period():
    """
    A period task that update the ansible task period
    """
    if PERIOD_TASK != "on":
        logger.debug('Period task off, skip')
        return
    key = '_JMS_TEST_ADMIN_USER_CONNECTIVITY_PERIOD'
    prev_execute_time = cache.get(key)
    if prev_execute_time:
        logger.debug("Test admin user connectivity, less than 40 minutes, skip")
        return
    cache.set(key, 1, 60*40)
    admin_users = AdminUser.objects.all()
    for admin_user in admin_users:
        task_name = _("Test admin user connectivity period: {}").format(admin_user.name)
        test_admin_user_connectivity_util(admin_user, task_name)
    cache.set(key, 1, 60*40)


@shared_task
def test_admin_user_connectivity_manual(admin_user):
    task_name = _("Test admin user connectivity: {}").format(admin_user.name)
    test_admin_user_connectivity_util(admin_user, task_name)
    return True


##  System user connective ##


@shared_task
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


@shared_task
def test_system_user_connectivity_manual(system_user):
    task_name = _("Test system user connectivity: {}").format(system_user)
    assets = system_user.get_all_assets()
    return test_system_user_connectivity_util(system_user, assets, task_name)


@shared_task
def test_system_user_connectivity_a_asset(system_user, asset):
    task_name = _("Test system user connectivity: {} => {}").format(
        system_user, asset
    )
    return test_system_user_connectivity_util(system_user, [asset], task_name)


@shared_task
def test_system_user_connectivity_period():
    if PERIOD_TASK != "on":
        logger.debug("Period task disabled, test system user connectivity pass")
        return
    system_users = SystemUser.objects.all()
    for system_user in system_users:
        task_name = _("Test system user connectivity period: {}").format(system_user)
        assets = system_user.get_all_assets()
        test_system_user_connectivity_util(system_user, assets, task_name)


####  Push system user tasks ####

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
    if system_user.password:
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


@shared_task
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


@shared_task
def push_system_user_to_assets_manual(system_user):
    assets = system_user.get_all_assets()
    task_name = _("Push system users to assets: {}").format(system_user.name)
    return push_system_user_util(system_user, assets, task_name=task_name)


@shared_task
def push_system_user_a_asset_manual(system_user, asset):
    task_name = _("Push system users to asset: {} => {}").format(
        system_user.name, asset
    )
    return push_system_user_util(system_user, [asset], task_name=task_name)


@shared_task
def push_system_user_to_assets(system_user, assets):
    task_name = _("Push system users to assets: {}").format(system_user.name)
    return push_system_user_util(system_user, assets, task_name)


@shared_task
@after_app_shutdown_clean_periodic
def test_system_user_connectability_period():
    pass


@shared_task
@after_app_shutdown_clean_periodic
def test_admin_user_connectability_period():
    pass


#### Test Asset user connectivity task ####

def get_test_asset_user_connectivity_tasks(asset):
    if asset.is_unixlike():
        tasks = const.TEST_ASSET_USER_CONN_TASKS
    elif asset.is_windows():
        tasks = const.TEST_WINDOWS_ASSET_USER_CONN_TASKS
    else:
        msg = _(
            "The asset {} system platform {} does not "
            "support run Ansible tasks".format(asset.hostname, asset.platform)
        )
        logger.info(msg)
        tasks = []
    return tasks


@shared_task
def test_asset_user_connectivity_util(asset_user, task_name, run_as_admin=False):
    """
    :param asset_user: <AuthBook>对象
    :param task_name:
    :param run_as_admin:
    :return:
    """
    from ops.utils import update_or_create_ansible_task

    if not check_asset_can_run_ansible(asset_user.asset):
        return

    tasks = get_test_asset_user_connectivity_tasks(asset_user.asset)
    if not tasks:
        logger.debug("No tasks ")
        return

    args = (task_name,)
    kwargs = {
        'hosts': [asset_user.asset], 'tasks': tasks,
        'pattern': 'all', 'options': const.TASK_OPTIONS,
        'created_by': asset_user.org_id,
    }
    if run_as_admin:
        kwargs["run_as_admin"] = True
    else:
        kwargs["run_as"] = asset_user.username
    task, created = update_or_create_ansible_task(*args, **kwargs)
    raw, summary = task.run()
    asset_user.set_connectivity(summary)


@shared_task
def test_asset_users_connectivity_manual(asset_users, run_as_admin=False):
    """
    :param asset_users: <AuthBook>对象
    """
    for asset_user in asset_users:
        task_name = _("Test asset user connectivity: {}").format(asset_user)
        test_asset_user_connectivity_util(asset_user, task_name, run_as_admin=run_as_admin)


# @shared_task
# @register_as_period_task(interval=3600)
# @after_app_ready_start
# @after_app_shutdown_clean_periodic
# def push_system_user_period():
#     for system_user in SystemUser.objects.all():
#         push_system_user_related_nodes(system_user)




