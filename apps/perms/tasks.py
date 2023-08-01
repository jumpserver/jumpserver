# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals

from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _

from common.const.crontab import CRONTAB_AT_AM_TEN
from common.utils import get_logger
from common.utils.timezone import local_now, dt_parser
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org
from perms.models import AssetPermission
from perms.notifications import (
    PermedAssetsWillExpireUserMsg,
    AssetPermsWillExpireForOrgAdminMsg,
)
from perms.utils import UserPermTreeExpireUtil

logger = get_logger(__file__)


@shared_task(verbose_name=_('Check asset permission expired'))
@register_as_period_task(interval=settings.PERM_EXPIRED_CHECK_PERIODIC)
@atomic()
@tmp_to_root_org()
def check_asset_permission_expired():
    """ 这里的任务要足够短，不要影响周期任务 """
    perms = AssetPermission.objects.get_expired_permissions()
    perm_ids = list(perms.distinct().values_list('id', flat=True))
    show_perm_ids = perm_ids[:5]
    logger.info(f'Checking expired permissions: {show_perm_ids} ...')
    UserPermTreeExpireUtil().expire_perm_tree_for_perms(perm_ids)


@shared_task(verbose_name=_('Send asset permission expired notification'))
@register_as_period_task(crontab=CRONTAB_AT_AM_TEN)
@atomic()
@tmp_to_root_org()
def check_asset_permission_will_expired():
    start = local_now()
    end = start + timedelta(days=3)

    user_asset_remain_day_mapper = defaultdict(dict)
    org_perm_remain_day_mapper = defaultdict(dict)

    asset_perms = AssetPermission.objects.filter(
        date_expired__gte=start,
        date_expired__lte=end
    ).distinct()

    for asset_perm in asset_perms:
        date_expired = dt_parser(asset_perm.date_expired)
        remain_days = (date_expired - start).days

        org = asset_perm.org
        # 资产授权按照组织分类
        if org in org_perm_remain_day_mapper[remain_days]:
            org_perm_remain_day_mapper[remain_days][org].add(asset_perm)
        else:
            org_perm_remain_day_mapper[remain_days][org] = {asset_perm, }

        # 计算每个用户即将过期的资产
        users = asset_perm.get_all_users()
        assets = asset_perm.get_all_assets()

        for u in users:
            if u in user_asset_remain_day_mapper[remain_days]:
                user_asset_remain_day_mapper[remain_days][u].update(assets)
            else:
                user_asset_remain_day_mapper[remain_days][u] = set(assets)

    for day_count, user_asset_mapper in user_asset_remain_day_mapper.items():
        for user, assets in user_asset_mapper.items():
            PermedAssetsWillExpireUserMsg(user, assets, day_count).publish_async()

    for day_count, org_perm_mapper in org_perm_remain_day_mapper.items():
        for org, perms in org_perm_mapper.items():
            org_admins = org.admins.all()
            for org_admin in org_admins:
                AssetPermsWillExpireForOrgAdminMsg(org_admin, perms, org, day_count).publish_async()
