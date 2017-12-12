# ~*~ coding: utf-8 ~*~
import json

from celery import shared_task
from django.core.cache import cache

from common.utils import get_object_or_none, capacity_convert, sum_capacity, encrypt_password, get_logger
from .models import SystemUser, AdminUser, Asset
from .const import ADMIN_USER_CONN_CACHE_KEY_PREFIX, SYSTEM_USER_CONN_CACHE_KEY_PREFIX


FORKS = 10
TIMEOUT = 60
logger = get_logger(__file__)


@shared_task
def update_assets_hardware_info(assets):
    """
    Using ansible api to update asset hardware info
    :param assets:  asset seq
    :return: result summary ['contacted': {}, 'dark': {}]
    """
    from ops.utils import run_adhoc
    name = "GET_ASSETS_HARDWARE_INFO"
    tasks = [
        {
            'name': name,
            'action': {
                'module': 'setup'
            }
        }
    ]
    hostname_list = [asset.hostname for asset in assets]
    result = run_adhoc(hostname_list, pattern='all', tasks=tasks,
                       name=name, run_as_admin=True)
    summary, result_raw = result.results_summary, result.results_raw
    for hostname, info in result_raw['ok'].items():
        if info:
            info = info[name]['ansible_facts']
        else:
            continue
        asset = get_object_or_none(Asset, hostname=hostname)
        if not asset:
            continue

        ___vendor = info['ansible_system_vendor']
        ___model = info['ansible_product_version']
        ___sn = info['ansible_product_serial']

        for ___cpu_model in info['ansible_processor']:
            if ___cpu_model.endswith('GHz'):
                break
        else:
            ___cpu_model = 'Unknown'
        ___cpu_count = info['ansible_processor_count']
        ___cpu_cores = info['ansible_processor_cores']
        ___memory = '%s %s' % capacity_convert('{} MB'.format(info['ansible_memtotal_mb']))
        disk_info = {}
        for dev, dev_info in info['ansible_devices'].items():
            if dev_info['removable'] == '0':
                disk_info[dev] = dev_info['size']
        ___disk_total = '%s %s' % sum_capacity(disk_info.values())
        ___disk_info = json.dumps(disk_info)

        ___platform = info['ansible_system']
        ___os = info['ansible_distribution']
        ___os_version = info['ansible_distribution_version']
        ___os_arch = info['ansible_architecture']
        ___hostname_raw = info['ansible_hostname']

        for k, v in locals().items():
            if k.startswith('___'):
                setattr(asset, k.strip('_'), v)
        asset.save()

    for hostname, task in summary['dark'].items():
        logger.warn("Update {} hardware info error: {}".format(
            hostname, task[name],
        ))

    return summary


@shared_task
def update_assets_hardware_period():
    """
    Update asset hardware period task
    :return:
    """
    assets = Asset.objects.filter(type__in=['Server', 'VM'])
    update_assets_hardware_info(assets)


@shared_task
def test_admin_user_connectability(admin_user):
    """
    Test asset admin user can connect or not. Using ansible api do that
    :param admin_user:
    :return:
    """
    from ops.utils import run_adhoc
    assets = admin_user.get_related_assets()
    hosts = [asset.hostname for asset in assets]
    tasks = [
        {
            "name": "TEST_ADMIN_CONNECTIVE",
            "action": {
                "module": "ping",
            }
        }
    ]
    result = run_adhoc(hosts, tasks=tasks, pattern="all", run_as_admin=True)
    return result.results_summary


@shared_task
def test_admin_user_connectability_period():
    # assets = Asset.objects.filter(type__in=['Server', 'VM'])
    admin_users = AdminUser.objects.all()
    for admin_user in admin_users:
        summary = test_admin_user_connectability(admin_user)

        cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + admin_user.name, summary, 60*60*60)
        for i in summary['contacted']:
            cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + i, 1, 60*60*60)

        for i in summary['dark']:
            cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + i, 0, 60*60*60)


@shared_task
def test_admin_user_connectability_manual(asset):
    from ops.utils import run_adhoc
    # assets = Asset.objects.filter(type__in=['Server', 'VM'])
    hosts = [asset.hostname]
    tasks = [
        {
            "name": "TEST_ADMIN_CONNECTIVE",
            "action": {
                "module": "ping",
            }
        }
    ]
    result = run_adhoc(hosts, tasks=tasks, pattern="all", run_as_admin=True)
    if result.results_summary['dark']:
        cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + asset.hostname, 0, 60*60*60)
        return False
    else:
        cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + asset.hostname, 1, 60*60* 60)
        return True


@shared_task
def test_system_user_connectability(system_user):
    """
    Test system cant connect his assets or not.
    :param system_user:
    :return:
    """
    from ops.utils import run_adhoc
    assets = system_user.get_clusters_assets()
    hosts = [asset.hostname for asset in assets]
    tasks = [
        {
            "name": "TEST_SYSTEM_USER_CONNECTIVE",
            "action": {
                "module": "ping",
            }
        }
    ]
    result = run_adhoc(hosts, tasks=tasks, pattern="all", run_as=system_user.name)
    return result.results_summary


@shared_task
def test_system_user_connectability_period():
    for system_user in SystemUser.objects.all():
        summary = test_system_user_connectability(system_user)
        cache.set(SYSTEM_USER_CONN_CACHE_KEY_PREFIX + system_user.name, summary, 60*60*60)


def get_push_system_user_tasks(system_user):
    tasks = [
        {
            'name': 'Add user',
            'action': {
                'module': 'user',
                'args': 'name={} shell={} state=present password={}'.format(
                    system_user.username, system_user.shell,
                    encrypt_password(system_user.password),
                ),
            }
        },
        {
            'name': 'Set authorized key',
            'action': {
                'module': 'authorized_key',
                'args': "user={} state=present key='{}'".format(
                    system_user.username, system_user.public_key
                )
            }
        },
        {
            'name': 'Set sudoers',
            'action': {
                'module': 'lineinfile',
                'args': "dest=/etc/sudoers state=present regexp='^{0} ALL=' "
                        "line='{0} ALL=(ALL) NOPASSWD: {1}' "
                        "validate='visudo -cf %s'".format(
                    system_user.username,
                    system_user.sudo,
                )
            }
        }
    ]
    return tasks


PUSH_SYSTEM_USER_PERIOD_TASK_NAME = 'PUSH SYSTEM USER [{}] PERIOD...'
PUSH_SYSTEM_USER_TASK_NAME = 'PUSH SYSTEM USER [{}] ASSETS'


def push_system_user(system_user, assets, name):
    from ops.utils import get_task_by_name, run_adhoc_object, \
        create_task, create_adhoc

    if system_user.auto_push and assets:
        task = get_task_by_name(name)
        if not task:
            task = create_task(name, created_by="System")
            task.save()
        tasks = get_push_system_user_tasks(system_user)
        hosts = [asset.hostname for asset in assets]
        options = {'forks': FORKS, 'timeout': TIMEOUT}

        adhoc = task.get_latest_adhoc()
        if not adhoc or adhoc.task != tasks or adhoc.hosts != hosts:
            adhoc = create_adhoc(task=task, tasks=tasks, pattern='all',
                                 options=options, hosts=hosts, run_as_admin=True)
        return run_adhoc_object(adhoc)


@shared_task
def push_system_user_period():
    logger.debug("Push system user period")
    for s in SystemUser.objects.filter(auto_push=True):
        assets = s.get_clusters_assets()

        name = PUSH_SYSTEM_USER_PERIOD_TASK_NAME.format(s.name)
        push_system_user(s, assets, name)


def push_system_user_to_assets_if_need(system_user, assets=None, asset_groups=None):
    assets_to_push = []
    system_user_assets = system_user.assets.all()
    if assets:
        assets_to_push.extend(assets)
    if asset_groups:
        for group in asset_groups:
            assets_to_push.extend(group.assets.all())

    assets_need_push = set(assets_to_push) - set(system_user_assets)
    if not assets_need_push:
        return
    logger.debug("Push system user {} to {} assets".format(
        system_user.name, ', '.join([asset.hostname for asset in assets_need_push])
    ))
    result = push_system_user(system_user, assets_need_push, PUSH_SYSTEM_USER_TASK_NAME)
    system_user.assets.add(*tuple(assets_need_push))
    return result
