# ~*~ coding: utf-8 ~*~
from __future__ import absolute_import, unicode_literals
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.db.transaction import atomic
from django.conf import settings
from celery import shared_task
from common.utils import get_logger
from common.utils.timezone import now, dt_formater, dt_parser
from users.models import User
from ops.celery.decorator import register_as_period_task
from assets.models import Node
from perms.models import RebuildUserTreeTask, AssetPermission
from perms.utils.asset.user_permission import rebuild_user_mapping_nodes_if_need_with_lock, lock

logger = get_logger(__file__)


@shared_task(queue='node_tree')
def rebuild_user_mapping_nodes_celery_task(user_id):
    user = User.objects.get(id=user_id)
    try:
        rebuild_user_mapping_nodes_if_need_with_lock(user)
    except lock.SomeoneIsDoingThis:
        pass


@shared_task(queue='node_tree')
def dispatch_mapping_node_tasks():
    user_ids = RebuildUserTreeTask.objects.all().values_list('user_id', flat=True).distinct()
    logger.info(f'>>> dispatch_mapping_node_tasks for users {list(user_ids)}')
    for id in user_ids:
        rebuild_user_mapping_nodes_celery_task.delay(id)


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

    ids = AssetPermission.objects.filter(
        date_expired__gte=start, date_expired__lte=end
    ).distinct().values_list('id', flat=True)
    logger.info(f'>>> checking {start} to {end} have {ids} expired')
    dispatch_process_expired_asset_permission.delay(list(ids))


@shared_task(queue='node_tree')
def dispatch_process_expired_asset_permission(asset_perms_id):
    user_ids = User.objects.filter(
        Q(assetpermissions__id__in=asset_perms_id) |
        Q(groups__assetpermissions__id__in=asset_perms_id)
    ).distinct().values_list('id', flat=True)
    RebuildUserTreeTask.objects.bulk_create(
        [RebuildUserTreeTask(user_id=user_id) for user_id in user_ids]
    )

    dispatch_mapping_node_tasks.delay()


def create_rebuild_user_tree_task(user_ids):
    RebuildUserTreeTask.objects.bulk_create(
        [RebuildUserTreeTask(user_id=i) for i in user_ids]
    )
    transaction.on_commit(dispatch_mapping_node_tasks.delay)


@shared_task(queue='node_tree')
def create_rebuild_user_tree_task_by_related_nodes_or_assets(node_ids, asset_ids):
    node_ids = set(node_ids)
    node_keys = set()
    nodes = Node.objects.filter(id__in=node_ids)
    for _node in nodes:
        node_keys.update(_node.get_ancestor_keys())
    node_ids.update(
        Node.objects.filter(key__in=node_keys).values_list('id', flat=True)
    )

    asset_perms_id = set()
    asset_perms_id.update(
        AssetPermission.objects.filter(
            assets__id__in=asset_ids
        ).values_list('id', flat=True).distinct()
    )
    asset_perms_id.update(
        AssetPermission.objects.filter(
            nodes__id__in=node_ids
        ).values_list('id', flat=True).distinct()
    )

    user_ids = set()
    user_ids.update(
        User.objects.filter(
            assetpermissions__id__in=asset_perms_id
        ).distinct().values_list('id', flat=True)
    )
    user_ids.update(
        User.objects.filter(
            groups__assetpermissions__id__in=asset_perms_id
        ).distinct().values_list('id', flat=True)
    )

    create_rebuild_user_tree_task(user_ids)
