# -*- coding: utf-8 -*-
#
import json
import re

from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import (
    capacity_convert, sum_capacity, get_logger
)
from . import const
from .utils import clean_hosts


logger = get_logger(__file__)
disk_pattern = re.compile(r'^hd|sd|xvd|vd|nv')
__all__ = [
    'update_assets_hardware_info_util', 'update_asset_hardware_info_manual',
    'update_assets_hardware_info_period',
]


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
        ___disk_total = '%.1f %s' % sum_capacity(disk_info.values())
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
    return True


@shared_task(queue="ansible")
def update_asset_hardware_info_manual(asset):
    task_name = _("Update asset hardware info: {}").format(asset.hostname)
    update_assets_hardware_info_util(
        [asset], task_name=task_name
    )


@shared_task(queue="ansible")
def update_assets_hardware_info_period():
    """
    Update asset hardware period task
    :return:
    """
    if not const.PERIOD_TASK_ENABLED:
        logger.debug("Period task disabled, update assets hardware info pass")
        return
