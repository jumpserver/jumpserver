from celery import shared_task
from django.utils.translation import gettext_lazy as _

from assets.const import AutomationTypes
from common.utils import get_logger, get_object_or_none
from orgs.utils import tmp_to_root_org, tmp_to_org

logger = get_logger(__file__)


def task_activity_callback(self, pid, trigger, tp, *args, **kwargs):
    model = AutomationTypes.get_type_model(tp)
    with tmp_to_root_org():
        instance = get_object_or_none(model, pk=pid)
    if not instance:
        return
    if not instance.latest_execution:
        return
    resource_ids = instance.latest_execution.get_all_asset_ids()
    return resource_ids, instance.org_id


@shared_task(
    queue='ansible', verbose_name=_('Asset execute automation'),
    activity_callback=task_activity_callback
)
def execute_asset_automation_task(pid, trigger, tp):
    model = AutomationTypes.get_type_model(tp)
    with tmp_to_root_org():
        instance = get_object_or_none(model, pk=pid)
    if not instance:
        logger.error("No automation task found: {}".format(pid))
        return
    with tmp_to_org(instance.org):
        instance.execute(trigger)
