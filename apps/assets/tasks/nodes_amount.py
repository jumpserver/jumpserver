from celery import shared_task
from django.utils.translation import gettext_lazy as _

from ops.celery.decorator import register_as_period_task
from assets.utils import check_node_assets_amount

from common.utils.lock import AcquireFailed
from common.utils import get_logger

logger = get_logger(__file__)


@shared_task(queue='celery_heavy_tasks')
@register_as_period_task(crontab='0 2 * * *')
def check_node_assets_amount_period_task():
    try:
        check_node_assets_amount()
    except AcquireFailed:
        logger.error(_('The task of self-checking is already running and cannot be started repeatedly'))
