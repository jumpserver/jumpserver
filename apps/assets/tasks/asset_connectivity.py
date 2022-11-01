# ~*~ coding: utf-8 ~*~
from celery import shared_task
from django.utils.translation import gettext_noop

from common.utils import get_logger
from orgs.utils import org_aware_func, tmp_to_root_org

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
        task_name = gettext_noop("Test assets connectivity. ")

    task_name = PingAutomation.generate_unique_name(task_name)
    data = {
        'name': task_name,
        'comment': ', '.join([str(i) for i in assets])
    }
    instance = PingAutomation.objects.create(**data)
    instance.assets.add(*assets)
    instance.execute()


@shared_task(queue="ansible")
def test_assets_connectivity_manual(asset_ids):
    from assets.models import Asset
    with tmp_to_root_org():
        assets = Asset.objects.filter(id__in=asset_ids)

    task_name = gettext_noop("Test assets connectivity: ")
    test_asset_connectivity_util(assets, task_name=task_name)


@shared_task(queue="ansible")
def test_node_assets_connectivity_manual(node_id):
    from assets.models import Node
    with tmp_to_root_org():
        node = Node.objects.get(id=node_id)

    task_name = gettext_noop("Test if the assets under the node are connectable: ")
    assets = node.get_all_assets()
    test_asset_connectivity_util(assets, task_name=task_name)
