# -*- coding: utf-8 -*-
#
from django.db.models.signals import m2m_changed, post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.db.models import Q

from users.models import User
from assets.models import Node, Asset
from common.utils import get_logger
from common.decorator import on_transaction_commit
from .models import AssetPermission, RemoteAppPermission
from .utils.asset_permission import AssetPermissionUtil
from .utils import update_users_tree_for_add, ADD, REMOVE


logger = get_logger(__file__)


@receiver([post_save, post_delete], sender=AssetPermission)
@on_transaction_commit
def on_permission_change(sender, action='', **kwargs):
    logger.debug('Asset permission changed, refresh user tree cache')
    AssetPermissionUtil.expire_all_user_tree_cache()

# Todo: 检查授权规则到期，从而修改授权规则


@receiver([pre_delete], sender=AssetPermission)
def on_permission_change(instance=None, **kwargs):
    if isinstance(instance, AssetPermission):
        nodes = list(instance.nodes.all())
        assets = list(instance.assets.all())
        user_ap_query_name = AssetPermission.users.field.related_query_name()
        group_ap_query_name = AssetPermission.user_groups.field.related_query_name()
        user_ap_q = Q(**{f'{user_ap_query_name}': instance})
        group_ap_q = Q(**{f'groups__{group_ap_query_name}': instance})
        users = list(User.objects.filter(user_ap_q | group_ap_q).distinct())
        update_users_tree_for_add(users, assets=assets, nodes=nodes, action=REMOVE)


@receiver(m2m_changed, sender=AssetPermission.nodes.through)
def on_permission_nodes_changed(sender, instance=None, action='', reverse=None, **kwargs):
    pk_set = kwargs.get('pk_set', [])

    user_ap_query_name = AssetPermission.users.field.related_query_name()
    group_ap_query_name = AssetPermission.user_groups.field.related_query_name()

    if isinstance(instance, AssetPermission):
        user_ap_q = Q(**{f'{user_ap_query_name}': instance})
        group_ap_q = Q(**{f'groups__{group_ap_query_name}': instance})
        users = list(User.objects.filter(user_ap_q | group_ap_q).distinct())
        nodes = list(Node.objects.filter(id__in=pk_set))
    else:
        user_ap_q = Q(**{f'{user_ap_query_name}__id__in': pk_set})
        group_ap_q = Q(**{f'groups__{group_ap_query_name}__id__in': pk_set})
        users = list(User.objects.filter(user_ap_q | group_ap_q).distinct())
        nodes = [instance]

    if action == 'post_add':
        _action = ADD
    elif action == 'post_remove':
        _action = REMOVE
    else:
        # Not support `clear`
        _action = None
    if _action:
        update_users_tree_for_add(users, nodes=nodes, action=_action)

    if action != 'post_add' and reverse:
        return
    logger.debug("Asset permission nodes change signal received")
    nodes = kwargs['model'].objects.filter(pk__in=pk_set)
    system_users = instance.system_users.all()
    for system_user in system_users:
        system_user.nodes.add(*tuple(nodes))


@receiver(m2m_changed, sender=AssetPermission.assets.through)
def on_permission_assets_changed(sender, instance=None, action='', reverse=None, **kwargs):
    pk_set = kwargs.get('pk_set', [])

    user_ap_query_name = AssetPermission.users.field.related_query_name()
    group_ap_query_name = AssetPermission.user_groups.field.related_query_name()

    if isinstance(instance, AssetPermission):
        user_ap_q = Q(**{f'{user_ap_query_name}': instance})
        group_ap_q = Q(**{f'groups__{group_ap_query_name}': instance})
        users = list(User.objects.filter(user_ap_q | group_ap_q).distinct())
        assets = list(Asset.objects.filter(id__in=pk_set))
    else:
        user_ap_q = Q(**{f'{user_ap_query_name}__id__in': pk_set})
        group_ap_q = Q(**{f'groups__{group_ap_query_name}__id__in': pk_set})
        users = list(User.objects.filter(user_ap_q | group_ap_q).distinct())
        assets = [instance]

    if action == 'post_add':
        _action = ADD
    elif action == 'post_remove':
        _action = REMOVE
    else:
        # Not support `clear`
        _action = None
    if _action:
        update_users_tree_for_add(users, assets=assets, action=_action)

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
    pk_set = kwargs.get('pk_set', [])

    if isinstance(instance, AssetPermission):
        nodes = list(instance.nodes.all())
        assets = list(instance.assets.all())
        users = list(User.objects.filter(id__in=pk_set).distinct())
    else:
        nodes = list(Node.objects.filter(granted_by_permissions__id__in=pk_set))
        assets = list(Asset.objects.filter(granted_by_permissions__id__in=pk_set))
        users = [instance]

    if action == 'post_add':
        _action = ADD
    elif action == 'post_remove':
        _action = REMOVE
    else:
        # Not support `clear`
        _action = None
    if _action:
        update_users_tree_for_add(users, nodes=nodes, assets=assets, action=_action)

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
    pk_set = kwargs.get('pk_set', [])

    if isinstance(instance, AssetPermission):
        nodes = list(instance.nodes.all())
        assets = list(instance.assets.all())
        users = list(User.objects.filter(groups__id__in=pk_set).distinct())
    else:
        nodes = list(Node.objects.filter(granted_by_permissions__id__in=pk_set))
        assets = list(Asset.objects.filter(granted_by_permissions__id__in=pk_set))
        users = list(User.objects.filter(groups=instance).distinct())

    if action == 'post_add':
        _action = ADD
    elif action == 'post_remove':
        _action = REMOVE
    else:
        # Not support `clear`
        _action = None
    if _action:
        update_users_tree_for_add(users, nodes=nodes, assets=assets, action=_action)

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


