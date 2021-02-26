from celery import shared_task
from django.utils.translation import gettext_lazy as _

from orgs.models import Organization
from orgs.utils import tmp_to_org
from ops.celery.decorator import register_as_period_task
from assets.utils import check_node_assets_amount

from common.utils.lock import AcquireFailed
from common.utils import get_logger

logger = get_logger(__file__)


@shared_task
def check_node_assets_amount_task(orgid=None):
    if orgid is None:
        orgs = [*Organization.objects.all(), Organization.default()]
    else:
        orgs = [Organization.get_instance(orgid)]

    for org in orgs:
        try:
            with tmp_to_org(org):
                check_node_assets_amount()
        except AcquireFailed:
            logger.error(_('The task of self-checking is already running and cannot be started repeatedly'))


@register_as_period_task(crontab='0 2 * * *')
@shared_task
def check_node_assets_amount_period_task():
    check_node_assets_amount_task()
