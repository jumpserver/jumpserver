from celery import shared_task

from common.utils import get_logger

logger = get_logger(__file__)


@shared_task
def refresh_org_cache_task(cache, *fields):
    logger.info(f'CACHE: refresh <org: {cache.get_current_org()}> {cache.key}.{fields}')
    cache.refresh(*fields)
