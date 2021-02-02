# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals
from datetime import timedelta

from django.db.transaction import atomic
from django.conf import settings
from celery import shared_task
from common.utils import get_logger
from common.utils.timezone import now, dt_formater, dt_parser
from ops.celery.decorator import register_as_period_task
from perms.models import AssetPermission
from perms.utils.asset.user_permission import UserGrantedTreeRefreshController

logger = get_logger(__file__)


@register_as_period_task(interval=settings.PERM_EXPIRED_CHECK_PERIODIC)
@shared_task(queue='celery_check_asset_perm_expired')
@atomic()
def check_asset_permission_expired():
    """
    这里的任务要足够短，不要影响周期任务
    """
    from settings.models import Setting

    setting_name = 'last_asset_perm_expired_check'

    end = now()
    default_start = end - timedelta(days=36000)  # Long long ago in china

    defaults = {'value': dt_formater(default_start)}
    setting, created = Setting.objects.get_or_create(
        name=setting_name, defaults=defaults
    )
    if created:
        start = default_start
    else:
        start = dt_parser(setting.value)
    setting.value = dt_formater(end)
    setting.save()

    asset_perm_ids = AssetPermission.objects.filter(
        date_expired__gte=start, date_expired__lte=end
    ).distinct().values_list('id', flat=True)
    asset_perm_ids = list(asset_perm_ids)
    logger.info(f'>>> checking {start} to {end} have {asset_perm_ids} expired')
    UserGrantedTreeRefreshController.add_need_refresh_by_asset_perm_ids_cross_orgs(asset_perm_ids)
