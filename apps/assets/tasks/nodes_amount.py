from celery import shared_task
from django.utils.translation import gettext_lazy as _

from orgs.models import Organization
from orgs.utils import tmp_to_org
from ops.celery.decorator import register_as_period_task
from assets.utils import check_node_assets_amount

from common.utils.lock import AcquireFailed
from common.utils import get_logger
from common.const.crontab import CRONTAB_AT_AM_TWO

logger = get_logger(__file__)


@shared_task(
    verbose_name=_('Check the amount of assets under the node'),
    description=_(
        """
        Manually verifying asset quantities updates the asset count for nodes under the 
        current organization. This task will be called in the following two cases: when updating 
        nodes and when the number of nodes exceeds 100
        """
    )
)
def check_node_assets_amount_task(org_id=None):
    if org_id is None:
        orgs = Organization.objects.all()
    else:
        orgs = [Organization.get_instance(org_id)]

    for org in orgs:
        try:
            with tmp_to_org(org):
                check_node_assets_amount()
        except AcquireFailed:
            error = _('The task of self-checking is already running '
                      'and cannot be started repeatedly')
            logger.error(error)


@shared_task(
    verbose_name=_('Periodic check the amount of assets under the node'),
    description=_(
        """
        Schedule the check_node_assets_amount_task to periodically update the asset count of 
        all nodes under all organizations
        """
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def check_node_assets_amount_period_task():
    check_node_assets_amount_task()
