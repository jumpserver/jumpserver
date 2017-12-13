# ~*~ coding: utf-8 ~*~
import json

from celery import shared_task
from django.core.cache import cache
from django.dispatch import receiver
from django.db.models.signals import post_save

from common.utils import get_object_or_none, capacity_convert, \
    sum_capacity, encrypt_password, get_logger
from common.celery import app as celery_app
from .models import SystemUser, AdminUser, Asset
from .const import ADMIN_USER_CONN_CACHE_KEY_PREFIX, SYSTEM_USER_CONN_CACHE_KEY_PREFIX, \
    UPDATE_ASSETS_HARDWARE_PERIOD_LOCK_KEY, TEST_ADMIN_USER_CONNECTABILITY_PEROID_KEY, \
    TEST_SYSTEM_USER_CONNECTABILITY_PEROID_KEY, PUSH_SYSTEM_USER_PERIOD_KEY
from .signals import on_app_ready


FORKS = 10
TIMEOUT = 60
logger = get_logger(__file__)
CACHE_MAX_TIME = 60*60*60


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
        logger.error("Update {} hardware info error: {}".format(
            hostname, task[name],
        ))

    return summary


@shared_task
def update_assets_hardware_period():
    """
    Update asset hardware period task
    :return:
    """
    if cache.get(UPDATE_ASSETS_HARDWARE_PERIOD_LOCK_KEY) == 1:
        logger.debug("Update asset hardware period task is running, passed")
        return {}
    try:
        cache.set(UPDATE_ASSETS_HARDWARE_PERIOD_LOCK_KEY, 1, CACHE_MAX_TIME)
        assets = Asset.objects.filter(type__in=['Server', 'VM'])
        return update_assets_hardware_info(assets)
    finally:
        cache.set(UPDATE_ASSETS_HARDWARE_PERIOD_LOCK_KEY, 0)


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
    if cache.get(TEST_ADMIN_USER_CONNECTABILITY_PEROID_KEY) == 1:
        logger.debug("Test admin user connectablity period task is running, passed")
        return

    logger.debug("Test admin user connectablity period task start")
    try:
        cache.set(TEST_ADMIN_USER_CONNECTABILITY_PEROID_KEY, 1, CACHE_MAX_TIME)
        admin_users = AdminUser.objects.all()
        for admin_user in admin_users:
            summary = test_admin_user_connectability(admin_user)

            cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + admin_user.name, summary, 60*60*60)
            for i in summary['contacted']:
                cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + i, 1, 60*60*60)

            for i, error in summary['dark'].items():
                cache.set(ADMIN_USER_CONN_CACHE_KEY_PREFIX + i, 0, 60*60*60)
                logger.error(error)
    finally:
        cache.set(TEST_ADMIN_USER_CONNECTABILITY_PEROID_KEY, 0)


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
    if cache.get(TEST_SYSTEM_USER_CONNECTABILITY_PEROID_KEY) == 1:
        logger.debug("Test admin user connectablity period task is running, passed")
        return

    logger.debug("Test system user connectablity period task start")
    try:
        cache.set(TEST_SYSTEM_USER_CONNECTABILITY_PEROID_KEY, 1, CACHE_MAX_TIME)
        for system_user in SystemUser.objects.all():
            summary = test_system_user_connectability(system_user)
            cache.set(SYSTEM_USER_CONN_CACHE_KEY_PREFIX + system_user.name, summary, 60*60*60)
    finally:
        cache.set(TEST_SYSTEM_USER_CONNECTABILITY_PEROID_KEY, 0)


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


def push_system_user(system_user, assets, task_name=None):
    from ops.utils import get_task_by_name, run_adhoc_object, \
        create_task, create_adhoc

    if system_user.auto_push and assets:
        if task_name is None:
            task_name = 'PUSH-SYSTEM-USER-{}'.format(system_user.name)

        task = get_task_by_name(task_name)
        if not task:
            logger.debug("Doesn't get task {}, create it".format(task_name))
            task = create_task(task_name, created_by="System")
            task.save()
        tasks = get_push_system_user_tasks(system_user)
        hosts = [asset.hostname for asset in assets]
        options = {'forks': FORKS, 'timeout': TIMEOUT}

        adhoc = task.get_latest_adhoc()
        if not adhoc or adhoc.task != tasks or adhoc.hosts != hosts:
            logger.debug("Task {} not exit or changed, create new version".format(task_name))
            adhoc = create_adhoc(task=task, tasks=tasks, pattern='all',
                                 options=options, hosts=hosts, run_as_admin=True)
        logger.debug("Task {} start execute".format(task_name))
        result = run_adhoc_object(adhoc)
        return result.results_summary
    else:
        msg = "Task {} does'nt execute, because not auto_push " \
              "is not True, or not assets".format(task_name)
        logger.debug(msg)
        return {}


@shared_task
def push_system_user_to_cluster_assets(system_user, task_name=None):
    logger.debug("{} task start".format(task_name))
    assets = system_user.get_clusters_assets()
    summary = push_system_user(system_user, assets, task_name)

    for h in summary.get("contacted", []):
        logger.debug("Push system user {} to {} success".format(system_user.name, h))
    for h, msg in summary.get('dark', {}).items():
        logger.error('Push system user {} to {} failed: {}'.format(
            system_user.name, h, msg
        ))
    return summary


@shared_task
def push_system_user_period():
    if cache.get(PUSH_SYSTEM_USER_PERIOD_KEY) == 1:
        logger.debug("push system user period task is running, passed")
        return

    logger.debug("Push system user period task start")
    try:
        cache.set(PUSH_SYSTEM_USER_PERIOD_KEY, 1, timeout=CACHE_MAX_TIME)
        for system_user in SystemUser.objects.filter(auto_push=True):
            task_name = 'PUSH-SYSTEM-USER-PERIOD'
            push_system_user_to_cluster_assets(system_user, task_name)
    finally:
        cache.set(PUSH_SYSTEM_USER_PERIOD_KEY, 0)


# def push_system_user_to_assets_if_need(system_user, assets=None, asset_groups=None):
#     assets_to_push = []
#     system_user_assets = system_user.assets.all()
#     if assets:
#         assets_to_push.extend(assets)
#     if asset_groups:
#         for group in asset_groups:
#             assets_to_push.extend(group.assets.all())
#
#     assets_need_push = set(assets_to_push) - set(system_user_assets)
#     if not assets_need_push:
#         return
#     logger.debug("Push system user {} to {} assets".format(
#         system_user.name, ', '.join([asset.hostname for asset in assets_need_push])
#     ))
#     result = push_system_user(system_user, assets_need_push, PUSH_SYSTEM_USER_TASK_NAME)
#     system_user.assets.add(*tuple(assets_need_push))
#     return result


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def update_asset_info(sender, instance=None, created=False, **kwargs):
    if instance and created:
        logger.debug("Receive asset create signal, update asset hardware info")
        update_assets_hardware_info.delay([instance])


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def test_admin_user_connective(sender, instance=None, created=False, **kwargs):
    if instance and created:
        logger.debug("Receive asset create signal, test admin user connectability")
        test_admin_user_connectability_manual.delay(instance)


@receiver(post_save, sender=SystemUser)
def push_system_user_on_change(sender, instance=None, created=False, **kwargs):
    if instance and instance.auto_push:
        logger.debug("System user `{}` auth changed, push it".format(instance.name))
        task_name = "PUSH-SYSTEM-USER-ON-CREATED-{}".format(instance.name)
        push_system_user_to_cluster_assets.delay(instance, task_name)


@receiver(post_save, sender=SystemUser)
def push_system_user_on_change(sender, instance=None, update_fields=None, **kwargs):
    fields_check = {'_password', '_private_key', '_public_key'}
    auth_changed = update_fields & fields_check if update_fields else None
    if instance and instance.auto_push and auth_changed:
        logger.debug("System user `{}` auth changed, push it".format(instance.name))
        task_name = "PUSH-SYSTEM-USER-ON-CREATED-{}".format(instance.name)
        push_system_user_to_cluster_assets.delay(instance, task_name)


@receiver(on_app_ready, dispatch_uid="my_unique_identifier")
def test_admin_user_on_app_ready(sender, **kwargs):
    logger.debug("Receive app ready signal, test admin connectability")
    test_admin_user_connectability_period.delay()


celery_app.conf['CELERYBEAT_SCHEDULE'].update(
    {
        'update_assets_hardware_period': {
            'task': 'assets.tasks.update_assets_hardware_period',
            'schedule': 60*60*24,
            'args': (),
        },
        'test-admin-user-connectability_period': {
            'task': 'assets.tasks.test_admin_user_connectability_period',
            'schedule': 60*60,
            'args': (),
        },
        'push_system_user_period': {
            'task': 'assets.tasks.push_system_user_period',
            'schedule': 60*60,
            'args': (),
        }
    }
)
