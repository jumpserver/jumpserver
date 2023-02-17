# -*- coding: utf-8 -*-
#

from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from assets.const import AutomationTypes
from common.utils import get_logger
from orgs.utils import tmp_to_org, current_org
from .common import quickstart_automation

logger = get_logger(__file__)
__all__ = [
    'gather_assets_facts_task',
    'update_node_assets_hardware_info_manual',
    'update_assets_hardware_info_manual',
]


@shared_task(
    queue="ansible", verbose_name=_('Gather assets facts'),
    activity_callback=lambda self, asset_ids, org_id, *args, **kwargs: (asset_ids, org_id)
)
def gather_assets_facts_task(asset_ids, org_id, task_name=None):
    from assets.models import GatherFactsAutomation
    if task_name is None:
        task_name = gettext_noop("Gather assets facts")
    task_name = GatherFactsAutomation.generate_unique_name(task_name)
    task_snapshot = {
        'assets': asset_ids,
    }
    tp = AutomationTypes.gather_facts

    with tmp_to_org(org_id):
        quickstart_automation(task_name, tp, task_snapshot)


def update_assets_hardware_info_manual(assets):
    task_name = gettext_noop("Update assets hardware info: ")
    asset_ids = [str(i.id) for i in assets]
    return gather_assets_facts_task.delay(asset_ids, str(current_org.id), task_name=task_name)


def update_node_assets_hardware_info_manual(node):
    asset_ids = node.get_all_asset_ids()
    asset_ids = [str(i) for i in asset_ids]
    task_name = gettext_noop("Update node asset hardware information: ")
    return gather_assets_facts_task.delay(asset_ids, str(current_org.id), task_name=task_name)
