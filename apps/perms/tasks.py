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
    AssetPermissionWillExpireSoonUserMsg,
)
from perms.utils import UserPermTreeExpireUtil

logger = get_logger(__file__)
EXPIRE_SOON_NOTICE_BATCH_SIZE = 200


@shared_task(
    verbose_name=_('Check asset permission expired'),
    description=_(
        """The cache of organizational collections, which have completed user authorization tree 
        construction, will expire. Therefore, expired collections need to be cleared from the 
        cache, and this task will be executed periodically based on the time interval specified 
        by PERM_EXPIRED_CHECK_PERIODIC in the system configuration file config.txt"""
    )
)
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
        date_expired__lte=end,
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


def _claim_one_expire_soon_notice(now):
    with atomic():
        asset_perm = AssetPermission.objects.select_for_update(skip_locked=True).filter(
            is_active=True,
            expire_soon_notice_enabled=True,
            expire_soon_notice_at__isnull=False,
            expire_soon_notice_at__lte=now,
            expire_soon_notice_sent_at__isnull=True,
            date_expired__gt=now,
        ).order_by('expire_soon_notice_at').first()
        if asset_perm is None:
            return None

        claimed_at = timezone.now()
        asset_perm.expire_soon_notice_sent_at = claimed_at
        asset_perm.save(update_fields=['expire_soon_notice_sent_at'])
        return asset_perm, claimed_at


def _publish_one_expire_soon_notice(now):
    claimed = _claim_one_expire_soon_notice(now)
    if claimed is None:
        return False

    asset_perm, claimed_at = claimed
    try:
        for user in asset_perm.get_all_users():
            AssetPermissionWillExpireSoonUserMsg(user, asset_perm).publish_async()
    except Exception:
        AssetPermission.objects.filter(
            id=asset_perm.id,
            expire_soon_notice_sent_at=claimed_at,
        ).update(expire_soon_notice_sent_at=None)
        raise
    else:
        return True


@shared_task(
    verbose_name=_('Send asset permission expiration-soon notification'),
    description=_(
        'Check due asset permission expiration-soon notices every minute and enqueue notifications'
    )
)
@register_as_period_task(interval=60)
@tmp_to_root_org()
def check_asset_permission_will_expire_soon():
    now = timezone.now()
    for _ in range(EXPIRE_SOON_NOTICE_BATCH_SIZE):
        if not _publish_one_expire_soon_notice(now):
            break
