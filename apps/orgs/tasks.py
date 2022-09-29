from celery import shared_task

from common.utils import get_logger

logger = get_logger(__file__)


@shared_task
def refresh_org_cache_task(*fields):
    from .caches import OrgResourceStatisticsCache
    OrgResourceStatisticsCache.refresh(*fields)
