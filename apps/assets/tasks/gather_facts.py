# -*- coding: utf-8 -*-
#
from celery import shared_task
from django.utils.translation import gettext_noop

from common.utils import get_logger
from orgs.utils import org_aware_func, tmp_to_root_org

logger = get_logger(__file__)
__all__ = [
    'update_assets_hardware_info_util',
    'update_node_assets_hardware_info_manual',
    'update_assets_hardware_info_manual',
]


@org_aware_func('assets')
def update_assets_hardware_info_util(assets=None, nodes=None, task_name=None):
    from assets.models import GatherFactsAutomation
    if not assets and not nodes:
        logger.info("No assets or nodes to update hardware info")
        return

    if task_name is None:
        task_name = gettext_noop("Update some assets hardware info. ")
    task_name = GatherFactsAutomation.generate_unique_name(task_name)
    comment = ''
    if assets:
        comment += 'asset:' + ', '.join([str(i) for i in assets]) + '\n'
    if nodes:
        comment += 'node:' + ', '.join([str(i) for i in nodes])

    data = {'name': task_name, 'comment': comment}
    instance = GatherFactsAutomation.objects.create(**data)

    if assets:
        instance.assets.add(*assets)
    if nodes:
        instance.nodes.add(*nodes)
    instance.execute()


@shared_task(queue="ansible")
def update_assets_hardware_info_manual(asset_ids):
    from assets.models import Asset
    with tmp_to_root_org():
        assets = Asset.objects.filter(id__in=asset_ids)
    task_name = gettext_noop("Update assets hardware info: ")
    update_assets_hardware_info_util(assets=assets, task_name=task_name)


@shared_task(queue="ansible")
def update_node_assets_hardware_info_manual(node_id):
    from assets.models import Node
    with tmp_to_root_org():
        node = Node.objects.get(id=node_id)

    task_name = gettext_noop("Update node asset hardware information: ")
    update_assets_hardware_info_util(nodes=[node], task_name=task_name)
