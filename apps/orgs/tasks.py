from celery import shared_task
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger

logger = get_logger(__file__)


@shared_task(
    verbose_name=_("Refresh organization cache"),
    description=_("Unused")
)
def refresh_org_cache_task(org_id, *fields):
    from .caches import OrgResourceStatisticsCache
    from .models import Organization

    org = Organization.get_instance(org_id)
    if org is None:
        logger.warning('Organization not found while refreshing cache: %s', org_id)
        return
    OrgResourceStatisticsCache(org).refresh(*fields)
