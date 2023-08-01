from celery import shared_task
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger

logger = get_logger(__file__)


@shared_task(verbose_name=_("Refresh organization cache"))
def refresh_org_cache_task(*fields):
    from .caches import OrgResourceStatisticsCache
    OrgResourceStatisticsCache.refresh(*fields)
