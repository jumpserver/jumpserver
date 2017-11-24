# ~*~ coding: utf-8 ~*~
from celery import shared_task
import json

from django.core.cache import cache

from ops.tasks import run_AdHoc
from common.utils import get_object_or_none, capacity_convert, sum_capacity
from .models import Asset


@shared_task
def update_assets_hardware_info(assets):
    task_tuple = (
        ('setup', ''),
    )
    summary, result = run_AdHoc(task_tuple, assets, record=False)
    for hostname, info in result['contacted'].items():
        if info:
            info = info[0]['ansible_facts']
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
    return summary


@shared_task
def update_assets_hardware_period():
    assets = Asset.objects.filter(type__in=['Server', 'VM'])
    update_assets_hardware_info(assets)


@shared_task
def test_admin_user_connective_period():
    assets = Asset.objects.filter(type__in=['Server', 'VM'])
    task_tuple = (
        ('ping', ''),
    )
    summary, _ = run_AdHoc(task_tuple, assets, record=False)
    for i in summary['success']:
        cache.set(i, '1', 2*60*60*60)

    for i, msg in summary['failed']:
        cache.set(i, '0', 60*60*60)
    return summary



