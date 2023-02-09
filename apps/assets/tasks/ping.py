# ~*~ coding: utf-8 ~*~
from celery import shared_task
from django.utils.translation import gettext_noop

from assets.const import AutomationTypes
from common.utils import get_logger
from orgs.utils import org_aware_func
from .common import quickstart_automation

logger = get_logger(__file__)

__all__ = [
    'test_assets_connectivity_task',
    'test_assets_connectivity_manual',
    'test_node_assets_connectivity_manual',
]


@shared_task
@org_aware_func('assets')
def test_assets_connectivity_task(assets, task_name=None):
    from assets.models import PingAutomation
    if task_name is None:
        task_name = gettext_noop("Test assets connectivity ")

    task_name = PingAutomation.generate_unique_name(task_name)
    task_snapshot = {'assets': [str(asset.id) for asset in assets]}
    quickstart_automation(task_name, AutomationTypes.ping, task_snapshot)


def test_assets_connectivity_manual(asset_ids):
    from assets.models import Asset
    assets = Asset.objects.filter(id__in=asset_ids)
    task_name = gettext_noop("Test assets connectivity ")
    test_assets_connectivity_task.delay(assets, task_name)


def test_node_assets_connectivity_manual(node_id):
    from assets.models import Node
    node = Node.objects.get(id=node_id)
    task_name = gettext_noop("Test if the assets under the node are connectable ")
    assets = node.get_all_assets()
    test_assets_connectivity_task.delay(*assets, task_name)
