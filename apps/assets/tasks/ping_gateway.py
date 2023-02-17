# ~*~ coding: utf-8 ~*~
from celery import shared_task
from django.utils.translation import gettext_noop, ugettext_lazy as _

from assets.const import AutomationTypes
from common.utils import get_logger
from orgs.utils import org_aware_func, tmp_to_org, current_org
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
@org_aware_func('assets')
def test_gateways_connectivity_task(asset_ids, org_id, local_port, task_name=None):
    from assets.models import PingAutomation
    if task_name is None:
        task_name = gettext_noop("Test gateways connectivity")

    task_name = PingAutomation.generate_unique_name(task_name)
    task_snapshot = {'assets': asset_ids, 'local_port': local_port}
    with tmp_to_org(org_id):
        quickstart_automation(task_name, AutomationTypes.ping_gateway, task_snapshot)


def test_gateways_connectivity_manual(gateway_ids, local_port):
    from assets.models import Asset
    gateways = Asset.objects.filter(id__in=gateway_ids).values_list('id', flat=True)
    task_name = gettext_noop("Test gateways connectivity")
    return test_gateways_connectivity_task.delay(gateways, str(current_org.id), local_port, task_name)
