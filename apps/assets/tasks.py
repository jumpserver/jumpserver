# ~*~ coding: utf-8 ~*~
import json

from celery import shared_task
from django.core.cache import cache
from django.dispatch import receiver
from django.db.models.signals import post_save

from common.utils import get_object_or_none, capacity_convert, \
    sum_capacity, encrypt_password, get_logger
from common.celery import register_as_period_task, after_app_shutdown_clean, \
    after_app_ready_start, app as celery_app

from .models import SystemUser, AdminUser, Asset
from . import const


FORKS = 10
TIMEOUT = 60
logger = get_logger(__file__)
CACHE_MAX_TIME = 60*60*60


@shared_task
def update_assets_hardware_info(result, **kwargs):
    """
    Using ops task run result, to update asset info

    @shared_task must be exit, because we using it as a task callback, is must
    be a celery task also
    :param result:
    :param kwargs: {task_name: ""}
    :return:
    """
    result_raw = result[0]
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
def update_assets_hardware_info_util(assets, task_name):
    """
    Using ansible api to update asset hardware info
    :param assets:  asset seq
    :param task_name: task_name running
    :return: result summary ['contacted': {}, 'dark': {}]
    """
    from ops.utils import update_or_create_ansible_task
    tasks = const.UPDATE_ASSETS_HARDWARE_TASKS
    hostname_list = [asset.hostname for asset in assets]
    task, _ = update_or_create_ansible_task(
        task_name, hosts=hostname_list, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    result = task.run()
    # Todo: may be somewhere using
    # Manual run callback function
    assets_updated = update_assets_hardware_info(result)
    return result


@shared_task
def update_assets_hardware_info_manual(assets):
    task_name = const.UPDATE_ASSETS_HARDWARE_MANUAL_TASK_NAME
    return update_assets_hardware_info_util(assets, task_name)


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def update_asset_info_on_created(sender, instance=None, created=False, **kwargs):
    if instance and created:
        msg = "Receive asset {} create signal, update asset hardware info".format(
            instance
        )
        logger.debug(msg)
        task_name = const.UPDATE_ASSETS_HARDWARE_ON_CREATE_TASK_NAME
        update_assets_hardware_info_util.delay([instance], task_name)


@celery_app.task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def update_assets_hardware_info_period():
    """
    Update asset hardware period task
    :return:
    """
    from ops.utils import update_or_create_ansible_task
    task_name = const.UPDATE_ASSETS_HARDWARE_PERIOD_TASK_NAME
    hostname_list = [asset.hostname for asset in Asset.objects.all()]
    tasks = const.UPDATE_ASSETS_HARDWARE_TASKS

    # Only create, schedule by celery beat
    _ = update_or_create_ansible_task(
        task_name, hosts=hostname_list, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
        interval=60*60*24, is_periodic=True, callback=update_assets_hardware_info.name,
    )


##  ADMIN USER CONNECTIVE  ##

@shared_task
def update_admin_user_connectability_info(result, **kwargs):
    admin_user = kwargs.get("admin_user")
    task_name = kwargs.get("task_name")
    if admin_user is None and task_name is not None:
        admin_user = task_name.split(":")[-1]

    _, summary = result
    cache_key = const.ADMIN_USER_CONN_CACHE_KEY.format(admin_user)
    cache.set(cache_key, summary, CACHE_MAX_TIME)

    for i in summary.get('contacted', []):
        asset_conn_cache_key = const.ASSET_ADMIN_CONN_CACHE_KEY.format(i)
        cache.set(asset_conn_cache_key, 1, CACHE_MAX_TIME)

    for i, msg in summary.get('dark', {}).items():
        asset_conn_cache_key = const.ASSET_ADMIN_CONN_CACHE_KEY.format(i)
        cache.set(asset_conn_cache_key, 0, CACHE_MAX_TIME)
        logger.error(msg)


@shared_task
def test_admin_user_connectability_util(admin_user, task_name):
    """
    Test asset admin user can connect or not. Using ansible api do that
    :param admin_user:
    :param task_name:
    :param force: Force update
    :return:
    """
    from ops.utils import update_or_create_ansible_task

    assets = admin_user.get_related_assets()
    hosts = [asset.hostname for asset in assets]
    tasks = const.TEST_ADMIN_USER_CONN_TASKS
    task, created = update_or_create_ansible_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    result = task.run()
    update_admin_user_connectability_info(result, admin_user=admin_user.name)
    return result


@celery_app.task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def test_admin_user_connectability_period():
    """
    A period task that update the ansible task period
    """
    from ops.utils import update_or_create_ansible_task
    admin_users = AdminUser.objects.all()
    for admin_user in admin_users:
        task_name = const.TEST_ADMIN_USER_CONN_PERIOD_TASK_NAME.format(admin_user.name)
        assets = admin_user.get_related_assets()
        hosts = [asset.hostname for asset in assets]
        tasks = const.TEST_ADMIN_USER_CONN_TASKS
        _ = update_or_create_ansible_task(
            task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
            interval=3600, is_periodic=True,
            callback=update_admin_user_connectability_info.name,
        )


@shared_task
def test_admin_user_connectability_manual(admin_user):
    task_name = const.TEST_ADMIN_USER_CONN_MANUAL_TASK_NAME.format(admin_user.name)
    return test_admin_user_connectability_util.delay(admin_user, task_name)


@shared_task
def test_asset_connectability_manual(asset):
    from ops.utils import update_or_create_ansible_task

    task_name = const.TEST_ASSET_CONN_TASK_NAME
    assets = [asset]
    hosts = [asset.hostname for asset in assets]
    tasks = const.TEST_ADMIN_USER_CONN_TASKS
    task, created = update_or_create_ansible_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    result = task.run()
    summary = result[1]
    if summary.get('dark'):
        cache.set(const.ASSET_ADMIN_CONN_CACHE_KEY.format(asset.hostname), 0, CACHE_MAX_TIME)
        return False, summary['dark']
    else:
        cache.set(const.ASSET_ADMIN_CONN_CACHE_KEY.format(asset.hostname), 1, CACHE_MAX_TIME)
        return True, ""


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def update_asset_conn_info_on_created(sender, instance=None, created=False,
                                      **kwargs):
    if instance and created:
        task_name = 'TEST-ASSET-CONN-WHEN-CREATED-{}'.format(instance)
        msg = "Receive asset {} create signal, test asset connectability".format(
            instance
        )
        logger.debug(msg)
        test_asset_connectability_manual.delay(instance, task_name)


##  System user connective ##


@shared_task
def update_system_user_connectablity_info(result, **kwargs):
    summary = result[1]
    task_name = kwargs.get("task_name")
    system_user = kwargs.get("system_user")
    if system_user is None:
        system_user = task_name.split(":")[-1]
    cache_key = const.SYSTEM_USER_CONN_CACHE_KEY.format(system_user)
    cache.set(cache_key, summary, CACHE_MAX_TIME)


@shared_task
def test_system_user_connectability_util(system_user, task_name):
    """
    Test system cant connect his assets or not.
    :param system_user:
    :param task_name:
    :return:
    """
    from ops.utils import update_or_create_ansible_task
    assets = system_user.get_clusters_assets()
    hosts = [asset.hostname for asset in assets]
    tasks = const.TEST_SYSTEM_USER_CONN_TASKS
    task, created = update_or_create_ansible_task(
        task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS,
        run_as=system_user.name, created_by="System",
    )
    result = task.run()
    update_system_user_connectablity_info(result, system_user=system_user.name)
    return result


@shared_task
def test_system_user_connectability_manual(system_user):
    task_name = const.TEST_SYSTEM_USER_CONN_MANUAL_TASK_NAME.format(system_user.name)
    return test_system_user_connectability_util(system_user, task_name)


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def test_system_user_connectability_period():
    from ops.utils import update_or_create_ansible_task
    system_users = SystemUser.objects.all()
    for system_user in system_users:
        task_name = const.TEST_SYSTEM_USER_CONN_PERIOD_TASK_NAME.format(
            system_user.name
        )
        assets = system_user.get_clusters_assets()
        hosts = [asset.hostname for asset in assets]
        tasks = const.TEST_SYSTEM_USER_CONN_TASKS
        _ = update_or_create_ansible_task(
            task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=False,  run_as=system_user.name,
            created_by='System', interval=3600, is_periodic=True,
            callback=update_admin_user_connectability_info.name,
        )


####  Push system user tasks ####

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
def push_system_user_util(system_user, task_name):
    from ops.utils import update_or_create_ansible_task

    tasks = get_push_system_user_tasks(system_user)
    assets = system_user.get_clusters_assets()
    hosts = [asset.hostname for asset in assets]
    task, _ = update_or_create_ansible_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System'
    )
    return task.run()


@shared_task
def push_system_user_to_cluster_assets_manual(system_user):
    task_name = const.PUSH_SYSTEM_USER_MANUAL_TASK_NAME.format(system_user.name)
    return push_system_user_util(system_user, task_name)


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def push_system_user_period():
    from ops.utils import update_or_create_ansible_task

    for system_user in SystemUser.objects.filter(auto_push=True):
        assets = system_user.get_clusters_assets()
        task_name = const.PUSH_SYSTEM_USER_PERIOD_TASK_NAME.format(system_user.name)
        hosts = [asset.hostname for asset in assets]
        tasks = get_push_system_user_tasks(system_user)

        _ = update_or_create_ansible_task(
            task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
            interval=60*60*24, is_periodic=True,
        )


@shared_task
def push_asset_system_users_util(asset, task_name, system_users=None):
    from ops.utils import update_or_create_ansible_task

    if system_users is None:
        system_users = asset.cluster.systemuser_set.all()

    tasks = []
    for system_user in system_users:
        if system_user.auto_push:
            tasks.extend(get_push_system_user_tasks(system_user))

    hosts = [asset.hostname]
    task, _ = update_or_create_ansible_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System'
    )
    return task.run()


@receiver(post_save, sender=Asset, dispatch_uid="my_unique_identifier")
def push_system_user_on_created(sender, instance=None, created=False, **kwargs):
    if instance and created:
        task_name = const.PUSH_SYSTEM_USERS_ON_ASSET_CREATE_TASK_NAME
        system_users = instance.cluster.systemuser_set.all()
        msg = "Receive asset {} create signal, push system users".format(
            instance
        )
        logger.debug(msg)
        push_asset_system_users_util.delay(instance, system_users, task_name=task_name)


@receiver(post_save, sender=SystemUser)
def push_system_user_on_change(sender, instance=None, update_fields=None, **kwargs):
    if instance and instance.auto_push:
        logger.debug("System user `{}` changed, push it".format(instance.name))
        task_name = "PUSH SYSTEM USER ON CREATED: {}".format(instance.name)
        push_system_user_util.delay(instance, task_name)










