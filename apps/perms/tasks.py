# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals

from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.transaction import atomic
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.const.crontab import CRONTAB_AT_AM_TEN
from common.utils import get_logger
from common.utils.timezone import dt_parser, local_now
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org
from perms.models import AssetPermission
from perms.notifications import (
    PermedAssetsWillExpireUserMsg,
    AssetPermsWillExpireForOrgAdminMsg,
)

logger = get_logger(__file__)


@shared_task(
    verbose_name=_('Send asset permission expired notification'),
    description=_(
        """Check every day at 10 a.m. and send a notification message to users associated with 
        assets whose authorization is about to expire, as well as to the organization's 
        administrators in advance, to remind them that the asset authorization
        will expire in a few days"""
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TEN)
@atomic()
@tmp_to_root_org()
def check_asset_permission_will_expired():
    first_notice_days = settings.PERM_EXPIRED_FIRST_NOTICE_DAYS
    daily_notice_days = settings.PERM_EXPIRED_DAILY_NOTICE_DAYS
    start = local_now()
    end = start + timedelta(days=first_notice_days + 1)

    user_asset_remain_day_mapper = defaultdict(dict)
    org_perm_remain_day_mapper = defaultdict(dict)

    asset_perms = AssetPermission.objects.filter(
        is_active=True,
        date_expired__gte=start,
        date_expired__lte=end
    ).distinct()

    for asset_perm in asset_perms:
        date_expired = dt_parser(asset_perm.date_expired)
        date_expired = timezone.localtime(date_expired).date()
        remain_days = (date_expired - start.date()).days
        should_notify = (
            remain_days == first_notice_days
            or 0 <= remain_days <= daily_notice_days
        )
        if not should_notify:
            continue

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
