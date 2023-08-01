# ~*~ coding: utf-8 ~*~
from celery import shared_task
from django.utils.translation import gettext_noop, gettext_lazy as _

from assets.const import AutomationTypes
from common.utils import get_logger
from orgs.utils import tmp_to_org, current_org
from .common import quickstart_automation

logger = get_logger(__file__)

__all__ = [
    'test_gateways_connectivity_task',
    'test_gateways_connectivity_manual',
]


@shared_task(
    verbose_name=_('Test gateways connectivity'), queue='ansible',
    activity_callback=lambda self, asset_ids, org_id, *args, **kwargs: (asset_ids, org_id)
)
def test_gateways_connectivity_task(asset_ids, org_id, local_port, task_name=None):
    from assets.models import PingAutomation
    if task_name is None:
        task_name = gettext_noop("Test gateways connectivity")

    task_name = PingAutomation.generate_unique_name(task_name)
    task_snapshot = {'assets': asset_ids, 'local_port': local_port}
    with tmp_to_org(org_id):
        quickstart_automation(task_name, AutomationTypes.ping_gateway, task_snapshot)


def test_gateways_connectivity_manual(gateway_ids, local_port):
    task_name = gettext_noop("Test gateways connectivity")
    gateway_ids = [str(i) for i in gateway_ids]
    return test_gateways_connectivity_task.delay(gateway_ids, str(current_org.id), local_port, task_name)
