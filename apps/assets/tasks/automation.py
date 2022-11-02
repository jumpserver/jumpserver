from celery import shared_task

from orgs.utils import tmp_to_root_org, tmp_to_org
from common.utils import get_logger, get_object_or_none

logger = get_logger(__file__)


@shared_task(queue='ansible')
def execute_automation(pid, trigger, mode):
    with tmp_to_root_org():
        instance = get_object_or_none(mode, pk=pid)
    if not instance:
        logger.error("No automation task found: {}".format(pid))
        return
    with tmp_to_org(instance.org):
        instance.execute(trigger)
