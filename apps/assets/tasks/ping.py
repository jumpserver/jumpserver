# ~*~ coding: utf-8 ~*~
import socket

from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from assets.const import AutomationTypes
from assets.models import Asset
from common.utils import get_logger, ColoredFilePrinter
from ops.celery.utils import get_celery_task_log_path
from orgs.utils import tmp_to_org, current_org
from .common import quickstart_automation

logger = get_logger(__file__)

__all__ = [
    'test_assets_connectivity_task',
    'test_assets_connectivity_manual',
    'test_node_assets_connectivity_manual',
    'test_assets_port_connectivity_manual',
]


@shared_task(
    verbose_name=_('Test assets connectivity'),
    queue='ansible',
    activity_callback=lambda self, asset_ids, org_id, *args, **kwargs: (asset_ids, org_id),
    description=_(
        "When clicking 'Test Asset Connectivity' in 'Asset Details - Basic Settings' this task will be executed"
    )
)
def test_assets_connectivity_task(asset_ids, org_id, task_name=None):
    from assets.models import PingAutomation
    if task_name is None:
        task_name = gettext_noop("Test assets connectivity")

    task_name = PingAutomation.generate_unique_name(task_name)
    task_snapshot = {'assets': asset_ids}
    with tmp_to_org(org_id):
        quickstart_automation(task_name, AutomationTypes.ping, task_snapshot)


def test_assets_connectivity_manual(assets):
    task_name = gettext_noop("Test assets connectivity ")
    asset_ids = [str(i.id) for i in assets]
    org_id = str(current_org.id)
    return test_assets_connectivity_task.delay(asset_ids, org_id, task_name)


def test_node_assets_connectivity_manual(node):
    task_name = gettext_noop("Test if the assets under the node are connectable ")
    asset_ids = node.get_all_asset_ids()
    asset_ids = [str(i) for i in asset_ids]
    org_id = str(current_org.id)
    return test_assets_connectivity_task.delay(asset_ids, org_id, task_name)


@shared_task(
    verbose_name=_('Test assets port connectivity'),
    activity_callback=lambda self, asset_ids, port, *args, **kwargs: (asset_ids,),
    description=_(
        "When clicking 'Test Asset Port Connectivity' in 'Asset List' this task will be executed"
    )
)
def test_assets_port_connectivity(asset_ids, port):
    log_path = get_celery_task_log_path(test_assets_port_connectivity.request.id)
    printer = ColoredFilePrinter(open(log_path, 'a'), flush_now=True)
    assets = Asset.objects.filter(id__in=asset_ids).values('name', 'address')
    msg = f"{_('Asset')}: %s {_('Test port')} {port}: %s"
    success, failed = [], []
    for asset in assets:
        asset_display = f'{asset["name"]}({asset["address"]})'
        try:
            socket.create_connection(
                (asset["address"], port), timeout=10, all_errors=True
            )
            printer.green(msg % (asset_display, _('Success')))
            success.append(asset)
        except ExceptionGroup:
            printer.red(msg % (asset_display, _('Failed')))
            failed.append(asset)
    printer.line()
    printer.info(
        _('Total {}, success {}, failure {}').format(len(assets), len(success), len(failed))
    )


def test_assets_port_connectivity_manual(assets, port):
    asset_ids = [str(i.id) for i in assets]
    return test_assets_port_connectivity.delay(asset_ids, port)
