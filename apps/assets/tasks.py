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
disk_pattern = re.compile(r'^hd|sd|xvd|vd')


@shared_task
def set_assets_hardware_info(result, **kwargs):
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
    for hostname, info in result_raw.get('ok', {}).items():
        info = info.get('setup', {}).get('ansible_facts', {})
        if not info:
            logger.error("Get asset info failed: {}".format(hostname))
            continue

        asset = get_object_or_none(Asset, hostname=hostname)
        if not asset:
            continue

        ___vendor = info.get('ansible_system_vendor', 'Unknown')
        ___model = info.get('ansible_product_name', 'Unknown')
        ___sn = info.get('ansible_product_serial', 'Unknown')

        for ___cpu_model in info.get('ansible_processor', []):
            if ___cpu_model.endswith('GHz') or ___cpu_model.startswith("Intel"):
                break
        else:
            ___cpu_model = 'Unknown'
        ___cpu_model = ___cpu_model[:64]
        ___cpu_count = info.get('ansible_processor_count', 0)
        ___cpu_cores = info.get('ansible_processor_cores', None) or len(info.get('ansible_processor', []))
        ___memory = '%s %s' % capacity_convert('{} MB'.format(info.get('ansible_memtotal_mb')))
        disk_info = {}
        for dev, dev_info in info.get('ansible_devices', {}).items():
            if disk_pattern.match(dev) and dev_info['removable'] == '0':
                disk_info[dev] = dev_info['size']
        ___disk_total = '%s %s' % sum_capacity(disk_info.values())
        ___disk_info = json.dumps(disk_info)

        ___platform = info.get('ansible_system', 'Unknown')
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
    hostname_list = [asset.hostname for asset in assets if asset.is_active and asset.is_unixlike()]
    task, created = update_or_create_ansible_task(
        task_name, hosts=hostname_list, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System',
    )
    result = task.run()
    # Todo: may be somewhere using
    # Manual run callback function
    set_assets_hardware_info(result)
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
    hostname_list = [
        asset.hostname for asset in Asset.objects.all()
        if asset.is_active and asset.is_unixlike()
    ]
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
    hosts = [asset.hostname for asset in assets
             if asset.is_active and asset.is_unixlike()]
    if not hosts:
        return
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
    admin_users = AdminUser.objects.all()
    for admin_user in admin_users:
        task_name = _("Test admin user connectability period: {}".format(admin_user.name))
        test_admin_user_connectability_util(admin_user, task_name)


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
    if not hosts:
        logger.info("No hosts, passed")
        return {}
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
    assets = system_user.assets
    hosts = [asset.hostname for asset in assets if asset.is_active and asset.is_unixlike()]
    tasks = const.TEST_SYSTEM_USER_CONN_TASKS
    if not hosts:
        logger.info("No hosts, passed")
        return {}
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
    task_name = _("Test system user connectability: {}").format(system_user)
    return test_system_user_connectability_util(system_user, task_name)


@shared_task
@register_as_period_task(interval=3600)
@after_app_ready_start
@after_app_shutdown_clean
def test_system_user_connectability_period():
    system_users = SystemUser.objects.all()
    for system_user in system_users:
        task_name = _("test system user connectability period: {}".format(system_user))
        test_system_user_connectability_util(system_user, task_name)


####  Push system user tasks ####

def get_push_system_user_tasks(system_user):
    # Set root as system user is dangerous
    if system_user.username == "root":
        return []

    tasks = []
    if system_user.password:
        tasks.append({
            'name': 'Add user {}'.format(system_user.username),
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
        tasks.append({
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
        })
    return tasks


@shared_task
def push_system_user_util(system_users, assets, task_name):
    from ops.utils import update_or_create_ansible_task
    tasks = []
    for system_user in system_users:
        if not system_user.is_need_push():
            msg = "push system user `{}` passed, may be not auto push or ssh " \
                  "protocol is not ssh".format(system_user.name)
            logger.info(msg)
            continue
        tasks.extend(get_push_system_user_tasks(system_user))

    if not tasks:
        logger.info("Not tasks, passed")
        return {}

    hosts = [asset.hostname for asset in assets if asset.is_active and asset.is_unixlike()]
    if not hosts:
        logger.info("Not hosts, passed")
        return {}
    task, created = update_or_create_ansible_task(
        task_name=task_name, hosts=hosts, tasks=tasks, pattern='all',
        options=const.TASK_OPTIONS, run_as_admin=True, created_by='System'
    )
    return task.run()


def get_node_push_system_user_task_name(system_user, node):
    return _("Push system user to node: {} => {}").format(
        system_user.name,
        node.value
    )


def push_system_user_to_node(system_user, node):
    assets = node.get_all_assets()
    task_name = get_node_push_system_user_task_name(system_user, node)
    push_system_user_util.delay([system_user], assets, task_name)


@shared_task
def push_system_user_related_nodes(system_user):
    if not system_user.is_need_push():
        msg = "push system user `{}` passed, may be not auto push or ssh " \
              "protocol is not ssh".format(system_user.name)
        logger.info(msg)
        return

    nodes = system_user.nodes.all()
    for node in nodes:
        push_system_user_to_node(system_user, node)


@shared_task
def push_system_user_to_assets_manual(system_user):
    push_system_user_related_nodes(system_user)


def push_node_system_users_to_asset(node, assets):
    system_users = []
    nodes = node.ancestor_with_node
    # 获取该节点所有父节点有的系统用户, 然后推送
    for n in nodes:
        system_users.extend(list(n.systemuser_set.all()))

    if system_users:
        task_name = _("Push system users to node: {}").format(node.value)
        push_system_user_util.delay(system_users, assets, task_name)


# @shared_task
# @register_as_period_task(interval=3600)
# @after_app_ready_start
# # @after_app_shutdown_clean
# def push_system_user_period():
#     for system_user in SystemUser.objects.all():
#         push_system_user_related_nodes(system_user)
