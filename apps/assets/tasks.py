# ~*~ coding: utf-8 ~*~
import json
import re

from celery import shared_task
from django.core.cache import cache
from django.utils.translation import ugettext as _

from common.utils import get_object_or_none, capacity_convert, \
    sum_capacity, encrypt_password, get_logger
from common.celery import register_as_period_task, after_app_shutdown_clean, \
    after_app_ready_start, app as celery_app

from .models import SystemUser, AdminUser, Asset, Cluster
from . import const


FORKS = 10
TIMEOUT = 60
logger = get_logger(__file__)
CACHE_MAX_TIME = 60*60*60
disk_pattern = re.compile(r'^hd|sd|xvd')


@shared_task
def set_assets_hardware_info(result, **kwargs):
    """
    Unsing ops task run result, to update asset info

    @shared_task must be exit, because we using it as a task callback, is must
    be a celery task also
    :param result:
    :param kwargs: {task_name: ""}
    :return:
    """
    result_raw = result[0]
    assets_updated = []
    for hostname, info in result_raw.get('ok', {}).items():
        if info:
            info = info['setup']['ansible_facts']
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
            if disk_pattern.match(dev) and dev_info['removable'] == '0':
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
    hostname_list = [asset.hostname for asset in assets]
    task, created = update_or_create_ansible_task(
        task_name, hosts=hostname_list, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    result = task.run()
    # Todo: may be somewhere using
    # Manual run callback function
    assets_updated = set_assets_hardware_info(result)
    return result


@shared_task
def update_asset_hardware_info_manual(asset):
    task_name = _("Update asset hardware info")
    return update_assets_hardware_info_util([asset], task_name=task_name)


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
    task_name = _("Update assets hardware info period")
    hostname_list = [asset.hostname for asset in Asset.objects.all()]
    tasks = const.UPDATE_ASSETS_HARDWARE_TASKS

    # Only create, schedule by celery beat
    update_or_create_ansible_task(
        task_name, hosts=hostname_list, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
        interval=60*60*24, is_periodic=True, callback=set_assets_hardware_info.name,
    )


##  ADMIN USER CONNECTIVE  ##

@shared_task
def set_admin_user_connectability_info(result, **kwargs):
    admin_user = kwargs.get("admin_user")
    task_name = kwargs.get("task_name")
    if admin_user is None and task_name is not None:
        admin_user = task_name.split(":")[-1]

    raw, summary = result
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
    set_admin_user_connectability_info(result, admin_user=admin_user.name)
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
        task_name = _("Test admin user connectability period: {}").format(admin_user)
        assets = admin_user.get_related_assets()
        hosts = [asset.hostname for asset in assets]
        tasks = const.TEST_ADMIN_USER_CONN_TASKS
        update_or_create_ansible_task(
            task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
            interval=3600, is_periodic=True,
            callback=set_admin_user_connectability_info.name,
        )


@shared_task
def test_admin_user_connectability_manual(admin_user):
    task_name = _("Test admin user connectability: {}").format(admin_user.name)
    return test_admin_user_connectability_util.delay(admin_user, task_name)


@shared_task
def test_asset_connectability_util(asset, task_name=None):
    from ops.utils import update_or_create_ansible_task

    if task_name is None:
        task_name = _("Test asset connectability")
    hosts = [asset.hostname]
    tasks = const.TEST_ADMIN_USER_CONN_TASKS
    task, created = update_or_create_ansible_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    result = task.run()
    summary = result[1]
    if summary.get('dark'):
        cache.set(const.ASSET_ADMIN_CONN_CACHE_KEY.format(asset.hostname), 0,
                  CACHE_MAX_TIME)
    else:
        cache.set(const.ASSET_ADMIN_CONN_CACHE_KEY.format(asset.hostname), 1,
                  CACHE_MAX_TIME)
    return summary


@shared_task
def test_asset_connectability_manual(asset):
    summary = test_asset_connectability_util(asset)

    if summary.get('dark'):
        return False, summary['dark']
    else:
        return True, ""


##  System user connective ##

@shared_task
def set_system_user_connectablity_info(result, **kwargs):
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
    set_system_user_connectablity_info(result, system_user=system_user.name)
    return result


@shared_task
def test_system_user_connectability_manual(system_user):
    task_name = "Test system user connectability: {}".format(system_user)
    return test_system_user_connectability_util(system_user, task_name)


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def test_system_user_connectability_period():
    from ops.utils import update_or_create_ansible_task
    system_users = SystemUser.objects.all()
    for system_user in system_users:
        task_name = _("Test system user connectability period: {}").format(
            system_user.name
        )
        assets = system_user.get_clusters_assets()
        hosts = [asset.hostname for asset in assets]
        tasks = const.TEST_SYSTEM_USER_CONN_TASKS
        update_or_create_ansible_task(
            task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=False,  run_as=system_user.name,
            created_by='System', interval=3600, is_periodic=True,
            callback=set_admin_user_connectability_info.name,
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
def push_system_user_util(system_users, assets, task_name):
    from ops.utils import update_or_create_ansible_task
    tasks = []
    for system_user in system_users:
        tasks.extend(get_push_system_user_tasks(system_user))

    print("Task: ", tasks)
    if not tasks:
        return

    hosts = [asset.hostname for asset in assets]
    task, created = update_or_create_ansible_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System'
    )
    return task.run()


@shared_task
def push_system_user_to_cluster_assets_manual(system_user):
    task_name = _("Push system user to cluster assets: {}").format(system_user.name)
    assets = system_user.get_clusters_assets()
    return push_system_user_util([system_user], assets, task_name)


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def push_system_user_period():
    from ops.utils import update_or_create_ansible_task
    clusters = Cluster.objects.all()

    for cluster in clusters:
        tasks = []
        system_users = [system_user for system_user in cluster.systemuser_set.all() if system_user.auto_push]
        if not system_users:
            return
        for system_user in system_users:
            tasks.extend(get_push_system_user_tasks(system_user))

        task_name = _("Push system user to cluster assets period: {}->{}").format(
            cluster.name, ', '.join(s.name for s in system_users)
        )
        hosts = [asset.hostname for asset in cluster.assets.all()]
        update_or_create_ansible_task(
            task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
            options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
            interval=60*60*24, is_periodic=True,
        )
