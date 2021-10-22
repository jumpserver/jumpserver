# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals
from datetime import timedelta
from collections import defaultdict

from django.db.transaction import atomic
from django.conf import settings
from celery import shared_task

from orgs.utils import tmp_to_root_org
from common.utils import get_logger
from common.utils.timezone import local_now, dt_formatter, dt_parser
from ops.celery.decorator import register_as_period_task
from perms.notifications import (
    PermedAssetsWillExpireUserMsg, AssetPermsWillExpireForOrgAdminMsg,
    PermedAppsWillExpireUserMsg, AppPermsWillExpireForOrgAdminMsg
)
from perms.models import AssetPermission, ApplicationPermission
from perms.utils.asset.user_permission import UserGrantedTreeRefreshController

logger = get_logger(__file__)


@register_as_period_task(interval=settings.PERM_EXPIRED_CHECK_PERIODIC)
@shared_task()
@atomic()
@tmp_to_root_org()
def check_asset_permission_expired():
    """
    这里的任务要足够短，不要影响周期任务
    """
    from settings.models import Setting

    setting_name = 'last_asset_perm_expired_check'

    end = local_now()
    default_start = end - timedelta(days=36000)  # Long long ago in china

    defaults = {'value': dt_formatter(default_start)}
    setting, created = Setting.objects.get_or_create(
        name=setting_name, defaults=defaults
    )
    if created:
        start = default_start
    else:
        start = dt_parser(setting.value)
    setting.value = dt_formatter(end)
    setting.save()

    asset_perm_ids = AssetPermission.objects.filter(
        date_expired__gte=start, date_expired__lte=end
    ).distinct().values_list('id', flat=True)
    asset_perm_ids = list(asset_perm_ids)
    logger.info(f'>>> checking {start} to {end} have {asset_perm_ids} expired')
    UserGrantedTreeRefreshController.add_need_refresh_by_asset_perm_ids_cross_orgs(asset_perm_ids)


@register_as_period_task(crontab='0 10 * * *')
@shared_task()
@atomic()
@tmp_to_root_org()
def check_asset_permission_will_expired():
    start = local_now()
    end = start + timedelta(days=3)

    user_asset_mapper = defaultdict(set)
    org_perm_mapper = defaultdict(set)

    asset_perms = AssetPermission.objects.filter(
        date_expired__gte=start,
        date_expired__lte=end
    ).distinct()

    for asset_perm in asset_perms:
        # 资产授权按照组织分类
        org_perm_mapper[asset_perm.org].add(asset_perm)

        # 计算每个用户即将过期的资产
        users = asset_perm.get_all_users()
        assets = asset_perm.get_all_assets()

        for u in users:
            user_asset_mapper[u].update(assets)

    for user, assets in user_asset_mapper.items():
        PermedAssetsWillExpireUserMsg(user, assets).publish_async()

    for org, perms in org_perm_mapper.items():
        org_admins = org.admins.all()
        for org_admin in org_admins:
            AssetPermsWillExpireForOrgAdminMsg(org_admin, perms, org).publish_async()


@register_as_period_task(crontab='0 10 * * *')
@shared_task()
@atomic()
@tmp_to_root_org()
def check_app_permission_will_expired():
    start = local_now()
    end = start + timedelta(days=3)

    app_perms = ApplicationPermission.objects.filter(
        date_expired__gte=start,
        date_expired__lte=end
    ).distinct()

    user_app_mapper = defaultdict(set)
    org_perm_mapper = defaultdict(set)

    for app_perm in app_perms:
        org_perm_mapper[app_perm.org].add(app_perm)

        users = app_perm.get_all_users()
        apps = app_perm.applications.all()
        for u in users:
            user_app_mapper[u].update(apps)

    for user, apps in user_app_mapper.items():
        PermedAppsWillExpireUserMsg(user, apps).publish_async()

    for org, perms in org_perm_mapper.items():
        org_admins = org.admins.all()
        for org_admin in org_admins:
            AppPermsWillExpireForOrgAdminMsg(org_admin, perms, org).publish_async()
