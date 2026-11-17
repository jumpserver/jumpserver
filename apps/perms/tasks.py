# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals

from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db.transaction import atomic
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from common.const.crontab import CRONTAB_AT_AM_TEN
from common.utils import get_logger
from common.utils.timezone import dt_parser, local_now
from ops.celery.decorator import register_as_period_task
from ops.celery.task_logging import TaskLog
from orgs.utils import tmp_to_root_org
from perms.models import AssetPermission
from perms.notifications import (
    PermedAssetsWillExpireUserMsg,
    AssetPermsWillExpireForOrgAdminMsg,
    AssetPermissionWillExpireSoonUserMsg,
)

logger = get_logger(__file__)
EXPIRE_SOON_NOTICE_BATCH_SIZE = 200


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
    with TaskLog(logger, gettext('Send asset permission expired notification')) as log:
        first_notice_days = settings.PERM_EXPIRED_FIRST_NOTICE_DAYS
        daily_notice_days = settings.PERM_EXPIRED_DAILY_NOTICE_DAYS
        start = local_now()
        end = start + timedelta(days=first_notice_days + 1)

        user_asset_remain_day_mapper = defaultdict(dict)
        user_permission_remain_day_mapper = defaultdict(lambda: defaultdict(set))
        org_perm_remain_day_mapper = defaultdict(dict)

        asset_perms = AssetPermission.objects.filter(
            is_active=True,
            date_expired__gte=start,
            date_expired__lte=end,
        ).distinct()

        for asset_perm in asset_perms:
            log.checked += 1
            date_expired = dt_parser(asset_perm.date_expired)
            date_expired = timezone.localtime(date_expired).date()
            remain_days = (date_expired - start.date()).days
            should_notify = (
                remain_days == first_notice_days
                or 0 <= remain_days <= daily_notice_days
            )
            if not should_notify:
                log.skip(gettext('The permission is outside the reminder window.'))
                continue
            log.processed += 1

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
                user_permission_remain_day_mapper[remain_days][u].add(asset_perm)
                if u in user_asset_remain_day_mapper[remain_days]:
                    user_asset_remain_day_mapper[remain_days][u].update(assets)
                else:
                    user_asset_remain_day_mapper[remain_days][u] = set(assets)

        for day_count, user_asset_mapper in user_asset_remain_day_mapper.items():
            for user, assets in user_asset_mapper.items():
                PermedAssetsWillExpireUserMsg(
                    user, assets, day_count, permissions=user_permission_remain_day_mapper[day_count][user],
                ).publish_async()
                log.metric(gettext('Notifications queued'), 1)

        for day_count, org_perm_mapper in org_perm_remain_day_mapper.items():
            for org, perms in org_perm_mapper.items():
                org_admins = org.admins.all()
                for org_admin in org_admins:
                    AssetPermsWillExpireForOrgAdminMsg(org_admin, perms, org, day_count).publish_async()
                    log.metric(gettext('Notifications queued'), 1)
        if log.processed and not log.metrics:
            log.skip(gettext('No users or administrators are available to receive reminders.'), 0)


def _claim_one_expire_soon_notice(now):
    with atomic():
        asset_perm = AssetPermission.objects.select_for_update(skip_locked=True).filter(
            is_active=True,
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
        return asset_perm


def _publish_one_expire_soon_notice(now, task_log=None):
    asset_perm = _claim_one_expire_soon_notice(now)
    if asset_perm is None:
        return False
    if task_log:
        task_log.checked += 1
    queued = failed = 0

    for user in asset_perm.get_all_users():
        try:
            AssetPermissionWillExpireSoonUserMsg(user, asset_perm).publish_async()
            queued += 1
        except Exception:
            failed += 1
            logger.exception(
                gettext('Unable to queue an asset permission expiration reminder: permission=%(permission)s; user=%(user)s.'),
                {'permission': asset_perm.id, 'user': user.id},
            )
    if task_log:
        task_log.metric(gettext('Notifications queued'), queued)
        if failed:
            task_log.fail(gettext('Unable to queue a notification.'))
        elif queued:
            task_log.processed += 1
        else:
            task_log.skip(gettext('No reminder was queued; recipients are missing or publication failed.'))
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
    with TaskLog(logger, gettext('Send asset permission expiration-soon notification')) as log:
        now = timezone.now()
        for _ in range(EXPIRE_SOON_NOTICE_BATCH_SIZE):
            if not _publish_one_expire_soon_notice(now, task_log=log):
                break
        if log.checked == EXPIRE_SOON_NOTICE_BATCH_SIZE:
            log.skip(gettext('The batch limit was reached; remaining records will be checked next time.'), 0)
