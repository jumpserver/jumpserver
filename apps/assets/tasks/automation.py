from celery import shared_task

from orgs.utils import tmp_to_root_org, tmp_to_org
from common.utils import get_logger, get_object_or_none

logger = get_logger(__file__)


@shared_task
def execute_change_secret_automation(pid, trigger):
    from assets.models import ChangeSecretAutomation
    with tmp_to_root_org():
        instance = get_object_or_none(ChangeSecretAutomation, pk=pid)
    if not instance:
        logger.error("No automation plan found: {}".format(pid))
        return
    with tmp_to_org(instance.org):
        instance.execute(trigger)
