from celery import shared_task

from ops.celery.decorator import register_as_period_task
from assets.utils import check_node_assets_amount
from common.utils import get_logger

logger = get_logger(__file__)


@register_as_period_task(crontab='* 2 * * *')
@shared_task(queue='celery_heavy_tasks')
def check_node_assets_amount_celery_task():
    check_node_assets_amount()
