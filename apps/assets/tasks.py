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
from . import const
from .signals import on_app_ready


FORKS = 10
TIMEOUT = 60
logger = get_logger(__file__)
CACHE_MAX_TIME = 60*60*60


def _update_asset_info(result_raw):
    assets_updated = []
    for hostname, info in result_raw['ok'].items():
        if info:
            info = info[const.UPDATE_ASSETS_HARDWARE_TASK_NAME]['ansible_facts']
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
        assets_updated.append(asset)
    return assets_updated


@shared_task
def update_assets_hardware_info(assets, task_name=None):
    """
    Using ansible api to update asset hardware info
    :param assets:  asset seq
    :param task_name: task_name running
    :return: result summary ['contacted': {}, 'dark': {}]
    """
    from ops.utils import create_or_update_task
    if task_name is None:
        task_name = const.UPDATE_ASSETS_HARDWARE_TASK_NAME
    tasks = const.UPDATE_ASSETS_HARDWARE_TASKS
    hostname_list = [asset.hostname for asset in assets]
    task = create_or_update_task(
        task_name, hosts=hostname_list, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    result = task.run()
    summary, result_raw = result.results_summary, result.results_raw
    # TOdo: may be somewhere using
    assets_updated = _update_asset_info(result_raw)
    return summary


@shared_task
def update_assets_hardware_period():
    """
    Update asset hardware period task
    :return:
    """
    task_name = const.UPDATE_ASSETS_HARDWARE_PERIOD_TASK_NAME
    if cache.get(const.UPDATE_ASSETS_HARDWARE_PERIOD_LOCK_KEY) == 1:
        msg = "Task {} is running or before long, passed this time".format(
            task_name
        )
        logger.debug(msg)
        return {}
    # Todo: set cache but not update, because we want also set it to as a
    # minimum update time too
    cache.set(const.UPDATE_ASSETS_HARDWARE_PERIOD_LOCK_KEY, 1, CACHE_MAX_TIME)
    assets = Asset.objects.filter(type__in=['Server', 'VM'])
    return update_assets_hardware_info(assets, task_name=task_name)


@shared_task
def test_admin_user_connectability(admin_user, force=False):
    """
    Test asset admin user can connect or not. Using ansible api do that
    :param admin_user:
    :param force: Force update
    :return:
    """
    from ops.utils import create_or_update_task

    task_name = const.TEST_ADMIN_USER_CONN_TASK_NAME.format(admin_user.name)
    lock_key = const.TEST_ADMIN_USER_CONN_LOCK_KEY.format(admin_user.name)

    if cache.get(lock_key, 0) == 1 and not force:
        logger.debug("Task {} is running or before along, passed this time")
        return {}

    assets = admin_user.get_related_assets()
    hosts = [asset.hostname for asset in assets]
    tasks = const.TEST_ADMIN_USER_CONN_TASKS
    task = create_or_update_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    cache.set(lock_key, 1, CACHE_MAX_TIME)
    result = task.run()
    cache_key = const.ADMIN_USER_CONN_CACHE_KEY.format(admin_user.name)
    cache.set(cache_key, result.results_summary, CACHE_MAX_TIME)

    for i in result.results_summary.get('contacted', []):
        asset_conn_cache_key = const.ASSET_ADMIN_CONN_CACHE_KEY.format(i)
        cache.set(asset_conn_cache_key, 1, CACHE_MAX_TIME)

    for i, msg in result.results_summary.get('dark', {}).items():
        asset_conn_cache_key = const.ASSET_ADMIN_CONN_CACHE_KEY.format(i)
        cache.set(asset_conn_cache_key, 0, CACHE_MAX_TIME)
        logger.error(msg)

    return result.results_summary


@shared_task
def test_admin_user_connectability_period():
    if cache.get(const.TEST_ADMIN_USER_CONN_PERIOD_LOCK_KEY) == 1:
        msg = "{} task is running or before long, passed this time".format(
            const.TEST_ADMIN_USER_CONN_PERIOD_TASK_NAME
        )
        logger.debug(msg)
        return

    logger.debug("Task {} start".format(const.TEST_ADMIN_USER_CONN_TASK_NAME))
    cache.set(const.TEST_ADMIN_USER_CONN_PERIOD_LOCK_KEY, 1, CACHE_MAX_TIME)
    admin_users = AdminUser.objects.all()
    for admin_user in admin_users:
        test_admin_user_connectability(admin_user)


@shared_task
def test_admin_user_connectability_manual(asset, task_name=None):
    from ops.utils import create_or_update_task
    if task_name is None:
        task_name = const.TEST_ASSET_CONN_TASK_NAME
    hosts = [asset.hostname]
    tasks = const.TEST_ADMIN_USER_CONN_TASKS
    task = create_or_update_task(
        task_name, tasks=tasks, hosts=hosts, run_as_admin=True,
        created_by='System', options=const.TASK_OPTIONS, pattern='all',
    )
    result = task.run()

    if result.results_summary['dark']:
        cache.set(const.ASSET_ADMIN_CONN_CACHE_KEY.format(asset.hostname), 0, CACHE_MAX_TIME)
        return False, result.results_summary['dark']
    else:
        cache.set(const.ASSET_ADMIN_CONN_CACHE_KEY.format(asset.hostname), 1, CACHE_MAX_TIME)
        return True, ""


@shared_task
def test_system_user_connectability(system_user, force=False):
    """
    Test system cant connect his assets or not.
    :param system_user:
    :param force
    :return:
    """
    from ops.utils import create_or_update_task
    lock_key = const.TEST_SYSTEM_USER_CONN_LOCK_KEY.format(system_user.name)
    task_name = const.TEST_SYSTEM_USER_CONN_TASK_NAME.format(system_user.name)
    if cache.get(lock_key, 0) == 1 and not force:
        logger.debug("Task {} is running or before long, passed this time".format(task_name))
        return {}
    assets = system_user.get_clusters_assets()
    hosts = [asset.hostname for asset in assets]
    tasks = const.TEST_SYSTEM_USER_CONN_TASKS
    task = create_or_update_task(
        task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS,
        run_as=system_user.name, created_by="System",
    )
    cache.set(lock_key, 1, CACHE_MAX_TIME)
    result = task.run()
    cache_key = const.SYSTEM_USER_CONN_CACHE_KEY.format(system_user.name)
    print("Set cache: {} {}".format(cache_key, result.results_summary))
    cache.set(cache_key, result.results_summary, CACHE_MAX_TIME)
    return result.results_summary


@shared_task
def test_system_user_connectability_period():
    lock_key = const.TEST_SYSTEM_USER_CONN_LOCK_KEY
    if cache.get(lock_key) == 1:
        logger.debug("{} task is running, passed this time".format(
            const.TEST_SYSTEM_USER_CONN_PERIOD_TASK_NAME
        ))
        return

    logger.debug("Task {} start".format(const.TEST_SYSTEM_USER_CONN_PERIOD_TASK_NAME))
    cache.set(lock_key, 1, CACHE_MAX_TIME)
    for system_user in SystemUser.objects.all():
        test_system_user_connectability(system_user)


def get_push_system_user_tasks(system_user):
    tasks = [
        {
            'name': 'Add user {}'.format(system_user.username),
            'action': {
                'module': 'user',
                'args': 'name={} shell={} state=present password={}'.format(
                    system_user.username, system_user.shell,
                    encrypt_password(system_user.password),
                ),
            }
        },
        {
            'name': 'Set {} authorized key'.format(system_user.username),
            'action': {
                'module': 'authorized_key',
                'args': "user={} state=present key='{}'".format(
                    system_user.username, system_user.public_key
                )
            }
        },
        {
            'name': 'Set {} sudo setting'.format(system_user.username),
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


@shared_task
def push_system_user(system_user, assets, task_name=None):
    from ops.utils import create_or_update_task

    if system_user.auto_push and assets:
        if task_name is None:
            task_name = 'PUSH-SYSTEM-USER-{}'.format(system_user.name)

        hosts = [asset.hostname for asset in assets]
        tasks = get_push_system_user_tasks(system_user)

        task = create_or_update_task(
            task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True, created_by='System'
        )
        result = task.run()
        for i in result.results_summary.get('contacted'):
            logger.debug("Push system user {} to {}  [OK]".format(
                system_user.name, i
            ))
        for i in result.results_summary.get('dark'):
            logger.error("Push system user {} to {}  [FAILED]".format(
                system_user.name, i
            ))
        return result.results_summary
    else:
        msg = "Task {} does'nt execute, because auto_push " \
              "is not True, or not assets".format(task_name)
        logger.debug(msg)
        return {}


@shared_task
def push_system_user_to_cluster_assets(system_user, force=False):
    lock_key = const.PUSH_SYSTEM_USER_LOCK_KEY
    task_name = const.PUSH_SYSTEM_USER_TASK_NAME.format(system_user.name)
    if cache.get(lock_key, 0) == 1 and not force:
        msg = "Task {} is running or before long, passed this time".format(
            task_name
        )
        logger.debug(msg)
        return {}

    logger.debug("Task {} start".format(task_name))
    assets = system_user.get_clusters_assets()
    summary = push_system_user(system_user, assets, task_name)
    return summary


@shared_task
def push_system_user_period():
    task_name = const.PUSH_SYSTEM_USER_PERIOD_TASK_NAME
    if cache.get(const.PUSH_SYSTEM_USER_PERIOD_LOCK_KEY) == 1:
        msg = "Task {} is running or before long, passed this time".format(
            task_name
        )
        logger.debug(msg)
        return
    logger.debug("Task {} start".format(task_name))
    cache.set(const.PUSH_SYSTEM_USER_PERIOD_LOCK_KEY, 1, timeout=CACHE_MAX_TIME)

    for system_user in SystemUser.objects.filter(auto_push=True):
        push_system_user_to_cluster_assets(system_user)


@shared_task
def push_asset_system_users(asset, system_users=None, task_name=None):
    from ops.utils import create_or_update_task
    if task_name is None:
        task_name = "PUSH-ASSET-SYSTEM-USER-{}".format(asset.hostname)

    if system_users is None:
        system_users = asset.cluster.systemuser_set.all()

    tasks = []
    for system_user in system_users:
        if system_user.auto_push:
            tasks.extend(get_push_system_user_tasks(system_user))

    hosts = [asset.hostname]

    task = create_or_update_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System'
    )
    result = task.run()
    return result.results_summary


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def update_asset_info_when_created(sender, instance=None, created=False, **kwargs):
    if instance and created:
        msg = "Receive asset {} create signal, update asset hardware info".format(
            instance
        )
        logger.debug(msg)
        task_name = "UPDATE-ASSET-HARDWARE-INFO-WHEN-CREATED"
        update_assets_hardware_info.delay([instance], task_name)


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def update_asset_conn_info_on_created(sender, instance=None, created=False, **kwargs):
    if instance and created:
        task_name = 'TEST-ASSET-CONN-WHEN-CREATED-{}'.format(instance)
        msg = "Receive asset {} create signal, test asset connectability".format(
            instance
        )
        logger.debug(msg)
        test_admin_user_connectability_manual.delay(instance, task_name)


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def push_system_user_on_created(sender, instance=None, created=False, **kwargs):
    if instance and created:
        task_name = 'PUSH-SYSTEM-USER-WHEN-ASSET-CREATED-{}'.format(instance)
        system_users = instance.cluster.systemuser_set.all()
        msg = "Receive asset {} create signal, push system users".format(
            instance
        )
        logger.debug(msg)
        push_asset_system_users.delay(instance, system_users, task_name=task_name)


@receiver(post_save, sender=SystemUser)
def push_system_user_on_auth_change(sender, instance=None, update_fields=None, **kwargs):
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
