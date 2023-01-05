# -*- coding: utf-8 -*-
#
from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from common.utils import get_logger
from assets.const import AutomationTypes
from orgs.utils import org_aware_func, tmp_to_root_org

from .common import automation_execute_start

logger = get_logger(__file__)
__all__ = [
    'update_assets_fact_util',
    'update_node_assets_hardware_info_manual',
    'update_assets_hardware_info_manual',
]


@org_aware_func('assets')
def update_assets_fact_util(assets=None, nodes=None, task_name=None):
    from assets.models import GatherFactsAutomation
    nodes = nodes or []
    assets = assets or []
    if not assets and not nodes:
        logger.info("No assets or nodes to update hardware info")
        return

    if task_name is None:
        task_name = gettext_noop("Update some assets hardware info. ")
    task_name = GatherFactsAutomation.generate_unique_name(task_name)

    child_snapshot = {
        'assets': [str(asset.id) for asset in assets],
        'nodes': [str(node.id) for node in nodes],
    }
    tp = AutomationTypes.gather_facts
    automation_execute_start(task_name, tp, child_snapshot)


@shared_task(queue="ansible", verbose_name=_('Manually update the hardware information of assets'))
def update_assets_hardware_info_manual(asset_ids):
    from assets.models import Asset
    with tmp_to_root_org():
        assets = Asset.objects.filter(id__in=asset_ids)
    task_name = gettext_noop("Update assets hardware info: ")
    update_assets_fact_util(assets=assets, task_name=task_name)


@shared_task(queue="ansible", verbose_name=_('Manually update the hardware information of assets under a node'))
def update_node_assets_hardware_info_manual(node_id):
    from assets.models import Node
    with tmp_to_root_org():
        node = Node.objects.get(id=node_id)

    task_name = gettext_noop("Update node asset hardware information: ")
    update_assets_fact_util(nodes=[node], task_name=task_name)
