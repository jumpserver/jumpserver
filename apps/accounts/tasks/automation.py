from celery import shared_task
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from orgs.utils import tmp_to_org

logger = get_logger(__file__)


def task_activity_callback(self, instance, *args):
    asset_ids = instance.get_all_asset_ids()
    return asset_ids, instance.org_id


@shared_task(
    queue='ansible', verbose_name=_('Account execute automation'),
    activity_callback=task_activity_callback
)
def execute_automation(instance, trigger):
    with tmp_to_org(instance.org):
        instance.execute(trigger)
