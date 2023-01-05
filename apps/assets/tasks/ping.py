# ~*~ coding: utf-8 ~*~
from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from common.utils import get_logger
from assets.const import AutomationTypes
from orgs.utils import org_aware_func, tmp_to_root_org

from .common import automation_execute_start

logger = get_logger(__file__)

__all__ = [
    'test_asset_connectivity_util',
    'test_assets_connectivity_manual',
    'test_node_assets_connectivity_manual',
]


@org_aware_func('assets')
def test_asset_connectivity_util(assets, task_name=None):
    from assets.models import PingAutomation
    if task_name is None:
        task_name = gettext_noop("Test assets connectivity ")

    task_name = PingAutomation.generate_unique_name(task_name)
    tp = AutomationTypes.ping
    child_snapshot = {
        'assets': [str(asset.id) for asset in assets],
    }
    automation_execute_start(task_name, tp, child_snapshot)


@shared_task(queue="ansible", verbose_name=_('Manually test the connectivity of a  asset'))
def test_assets_connectivity_manual(asset_ids):
    from assets.models import Asset
    with tmp_to_root_org():
        assets = Asset.objects.filter(id__in=asset_ids)

    task_name = gettext_noop("Test assets connectivity ")
    test_asset_connectivity_util(assets, task_name=task_name)


@shared_task(queue="ansible", verbose_name=_('Manually test the connectivity of assets under a node'))
def test_node_assets_connectivity_manual(node_id):
    from assets.models import Node
    with tmp_to_root_org():
        node = Node.objects.get(id=node_id)

    task_name = gettext_noop("Test if the assets under the node are connectable ")
    assets = node.get_all_assets()
    test_asset_connectivity_util(assets, task_name=task_name)
