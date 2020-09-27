from celery import shared_task

from assets.utils import check_node_assets_amount
from common.utils import get_logger
from common.utils.timezone import now

logger = get_logger(__file__)


@shared_task()
def check_node_assets_amount_celery_task():
    logger.info(f'>>> {now()} begin check_node_assets_amount_celery_task ...')
    check_node_assets_amount()
    logger.info(f'>>> {now()} end check_node_assets_amount_celery_task ...')
