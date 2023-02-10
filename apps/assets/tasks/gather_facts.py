# -*- coding: utf-8 -*-
#
from itertools import chain

from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from assets.const import AutomationTypes
from common.utils import get_logger
from orgs.utils import tmp_to_org
from .common import quickstart_automation

logger = get_logger(__file__)
__all__ = [
    'gather_assets_facts_task',
    'update_node_assets_hardware_info_manual',
    'update_assets_hardware_info_manual',
]


@shared_task(queue="ansible", verbose_name=_('Gather assets facts'))
def gather_assets_facts_task(assets=None, nodes=None, task_name=None):
    from assets.models import GatherFactsAutomation
    if task_name is None:
        task_name = gettext_noop("Gather assets facts")
    task_name = GatherFactsAutomation.generate_unique_name(task_name)

    nodes = nodes or []
    assets = assets or []
    resources = chain(assets, nodes)
    if not resources:
        raise ValueError("nodes or assets must be given")
    org_id = list(resources)[0].org_id
    task_snapshot = {
        'assets': [str(asset.id) for asset in assets],
        'nodes': [str(node.id) for node in nodes],
    }
    tp = AutomationTypes.gather_facts

    with tmp_to_org(org_id):
        quickstart_automation(task_name, tp, task_snapshot)


def update_assets_hardware_info_manual(asset_ids):
    from assets.models import Asset
    assets = Asset.objects.filter(id__in=asset_ids)
    task_name = gettext_noop("Update assets hardware info: ")
    return gather_assets_facts_task.delay(assets=assets, task_name=task_name)


def update_node_assets_hardware_info_manual(node_id):
    from assets.models import Node
    node = Node.objects.get(id=node_id)
    task_name = gettext_noop("Update node asset hardware information: ")
    return gather_assets_facts_task.delay(nodes=[node], task_name=task_name)
