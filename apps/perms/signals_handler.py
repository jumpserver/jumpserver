# -*- coding: utf-8 -*-
#
from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver

from common.utils import get_logger
from common.decorator import on_transaction_commit
from .models import AssetPermission, RemoteAppPermission
from .utils.asset_permission import AssetPermissionUtil


logger = get_logger(__file__)


@receiver([post_save, post_delete], sender=AssetPermission)
@on_transaction_commit
def on_permission_change(sender, action='', **kwargs):
    logger.debug('Asset permission changed, refresh user tree cache')
    AssetPermissionUtil.expire_all_user_tree_cache()

# Todo: 检查授权规则到期，从而修改授权规则


@receiver(m2m_changed, sender=AssetPermission.nodes.through)
def on_permission_nodes_changed(sender, instance=None, action='', reverse=None, **kwargs):
    if action != 'post_add' and reverse:
        return
    logger.debug("Asset permission nodes change signal received")
    nodes = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
    system_users = instance.system_users.all()
    for system_user in system_users:
        system_user.nodes.add(*tuple(nodes))


@receiver(m2m_changed, sender=AssetPermission.assets.through)
def on_permission_assets_changed(sender, instance=None, action='', reverse=None, **kwargs):
    if action != 'post_add' and reverse:
        return
    logger.debug("Asset permission assets change signal received")
    assets = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
    system_users = instance.system_users.all()
    for system_user in system_users:
        system_user.assets.add(*tuple(assets))


@receiver(m2m_changed, sender=AssetPermission.system_users.through)
def on_asset_permission_system_users_changed(sender, instance=None, action='',
                                             reverse=False, **kwargs):
    if action != 'post_add' and reverse:
        return
    logger.debug("Asset permission system_users change signal received")
    system_users = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
    assets = instance.assets.all().values_list('id', flat=True)
    nodes = instance.nodes.all().values_list('id', flat=True)
    users = instance.users.all().values_list('id', flat=True)
    groups = instance.user_groups.all().values_list('id', flat=True)
    for system_user in system_users:
        system_user.nodes.add(*tuple(nodes))
        system_user.assets.add(*tuple(assets))
        if system_user.username_same_with_user:
            system_user.groups.add(*tuple(groups))
            system_user.users.add(*tuple(users))


@receiver(m2m_changed, sender=AssetPermission.users.through)
def on_asset_permission_users_changed(sender, instance=None, action='',
                                      reverse=False, **kwargs):
    if action != 'post_add' and reverse:
        return
    logger.debug("Asset permission users change signal received")
    users = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
    system_users = instance.system_users.all()

    for system_user in system_users:
        if system_user.username_same_with_user:
            system_user.users.add(*tuple(users))


@receiver(m2m_changed, sender=AssetPermission.user_groups.through)
def on_asset_permission_user_groups_changed(sender, instance=None, action='',
                                            reverse=False, **kwargs):
    if action != 'post_add' and reverse:
        return
    logger.debug("Asset permission user groups change signal received")
    groups = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
    system_users = instance.system_users.all()

    for system_user in system_users:
        if system_user.username_same_with_user:
            system_user.groups.add(*tuple(groups))


@receiver(m2m_changed, sender=RemoteAppPermission.system_users.through)
def on_remote_app_permission_system_users_changed(sender, instance=None,
                                                  action='', reverse=False, **kwargs):
    if action != 'post_add' or reverse:
        return
    system_users = kwargs['model'].objects.filter(pk__in=kwargs['pk_set'])
    logger.debug("Remote app permission system_users change signal received")
    assets = instance.remote_apps.all().values_list('asset__id', flat=True)
    users = instance.users.all().values_list('id', flat=True)
    groups = instance.user_groups.all().values_list('id', flat=True)
    for system_user in system_users:
        system_user.assets.add(*tuple(assets))
        if system_user.username_same_with_user:
            system_user.groups.add(*tuple(groups))
            system_user.users.add(*tuple(users))


@receiver(m2m_changed, sender=RemoteAppPermission.users.through)
def on_remoteapps_permission_users_changed(sender, instance=None, action='',
                                      reverse=False, **kwargs):
    on_asset_permission_users_changed(sender, instance=instance, action=action,
                                      reverse=reverse, **kwargs)


@receiver(m2m_changed, sender=RemoteAppPermission.user_groups.through)
def on_remoteapps_permission_user_groups_changed(sender, instance=None, action='',
                                            reverse=False, **kwargs):
    on_asset_permission_user_groups_changed(sender, instance=instance,
                                            action=action, reverse=reverse, **kwargs)
