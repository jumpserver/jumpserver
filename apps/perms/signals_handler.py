# -*- coding: utf-8 -*-
#
from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver

from common.utils import get_logger
from common.decorator import on_transaction_commit
from .models import AssetPermission
from .utils.asset_permission import AssetPermissionUtilV2


logger = get_logger(__file__)


@receiver([post_save, post_delete], sender=AssetPermission)
@on_transaction_commit
def on_permission_change(sender, action='', **kwargs):
    logger.debug('Asset permission changed, refresh user tree cache')
    AssetPermissionUtilV2.expire_all_user_tree_cache()

# Todo: 检查授权规则到期，从而修改授权规则


@receiver(m2m_changed, sender=AssetPermission.nodes.through)
def on_permission_nodes_changed(sender, instance=None, action='', **kwargs):
    if action != 'post_add':
        return
    if isinstance(instance, AssetPermission):
        logger.debug("Asset permission nodes change signal received")
        nodes = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        system_users = instance.system_users.all()
        for system_user in system_users:
            system_user.nodes.add(*tuple(nodes))


@receiver(m2m_changed, sender=AssetPermission.assets.through)
def on_permission_assets_changed(sender, instance=None, action='', **kwargs):
    if action != 'post_add':
        return
    if isinstance(instance, AssetPermission):
        logger.debug("Asset permission assets change signal received")
        assets = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        system_users = instance.system_users.all()
        for system_user in system_users:
            system_user.assets.add(*tuple(assets))


@receiver(m2m_changed, sender=AssetPermission.system_users.through)
def on_permission_system_users_changed(sender, instance=None, action='', **kwargs):
    if action != 'post_add':
        return
    if isinstance(instance, AssetPermission):
        system_users = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
        logger.debug("Asset permission system_users change signal received")
        assets = instance.assets.all().values_list('id', flat=True)
        nodes = instance.nodes.all().values_list('id', flat=True)
        for system_user in system_users:
            system_user.nodes.add(*tuple(nodes))
            system_user.assets.add(*tuple(assets))

