from celery import shared_task
from django.utils.translation import gettext_lazy as _

from orgs.utils import tmp_to_root_org, tmp_to_org
from common.utils import get_logger, get_object_or_none
from assets.const import AutomationTypes

logger = get_logger(__file__)


@shared_task(queue='ansible', verbose_name=_('Asset execute automation'))
def execute_automation(pid, trigger, tp):
    model = AutomationTypes.get_type_model(tp)
    with tmp_to_root_org():
        instance = get_object_or_none(model, pk=pid)
    if not instance:
        logger.error("No automation task found: {}".format(pid))
        return
    with tmp_to_org(instance.org):
        instance.execute(trigger)
