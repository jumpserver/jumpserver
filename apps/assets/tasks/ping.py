# ~*~ coding: utf-8 ~*~
from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from common.utils import get_logger
from assets.const import AutomationTypes, GATEWAY_NAME
from orgs.utils import org_aware_func

from .common import automation_execute_start

logger = get_logger(__file__)

__all__ = [
    'test_asset_connectivity_util',
    'test_assets_connectivity_manual',
    'test_node_assets_connectivity_manual',
]


def test_connectivity_util(assets, tp, task_name, local_port=None):
    if not assets:
        return

    if local_port is None:
        child_snapshot = {}
    else:
        child_snapshot = {'local_port': local_port}

    child_snapshot['assets'] = [str(asset.id) for asset in assets]
    automation_execute_start(task_name, tp, child_snapshot)


@org_aware_func('assets')
def test_asset_connectivity_util(assets, task_name=None, local_port=None):
    from assets.models import PingAutomation
    if task_name is None:
        task_name = gettext_noop("Test assets connectivity ")

    task_name = PingAutomation.generate_unique_name(task_name)

    gateway_assets = assets.filter(platform__name=GATEWAY_NAME)
    test_connectivity_util(
        gateway_assets, AutomationTypes.ping_gateway, task_name, local_port
    )

    non_gateway_assets = assets.exclude(platform__name=GATEWAY_NAME)
    test_connectivity_util(non_gateway_assets, AutomationTypes.ping, task_name)


@shared_task(queue="ansible", verbose_name=_('Manually test the connectivity of a asset'))
def test_assets_connectivity_manual(asset_ids, local_port=None):
    from assets.models import Asset
    assets = Asset.objects.filter(id__in=asset_ids)
    task_name = gettext_noop("Test assets connectivity ")
    test_asset_connectivity_util(assets, task_name, local_port)


@shared_task(queue="ansible", verbose_name=_('Manually test the connectivity of assets under a node'))
def test_node_assets_connectivity_manual(node_id, local_port=None):
    from assets.models import Node
    node = Node.objects.get(id=node_id)
    task_name = gettext_noop("Test if the assets under the node are connectable ")
    assets = node.get_all_assets()
    test_asset_connectivity_util(assets, task_name, local_port)
