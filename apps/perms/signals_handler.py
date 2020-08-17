# -*- coding: utf-8 -*-
#
from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver
from django.db.models import F, Count

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


from itertools import chain
from assets.models import Node, Asset
from perms.models import GrantedNode
from users.models import User
from typing import List


def inc_granted_count(obj, value=1):
    obj._granted_count = getattr(obj, '_granted_count', 0) + value


def inc_asset_granted_count(obj, value=1):
    obj._granted_count = getattr(obj, '_asset_granted_count', 0) + value


ADD = object()
REMOVE = object()


def update_users_tree_for_add(granted_nodes: List[Node], assets: List[Asset],
                              users: List[User], action=ADD):
    """
    `_granted_count` 授权次数，等于节点数或者资产数
    """

    # 查询授权`Asset`关联的 `Node`
    asset_granted_nodes = Node.objects.filter(
        assets__in=assets
    ).annotate(
        _granted_count=Count('assets', distinct=True),
        _asset_granted_count=Count('assets', distinct=True),
        _granted=False
    ).distinct()
    # 授权的 `Node`
    for n in granted_nodes:
        inc_granted_count(n)
        n._granted = True
    # 资产授权节点与直接授权节点总共的祖先`key`，因为两者可能会重叠，所以字典的键复杂
    ancestor_keys_map = {(n, n._granted): n.get_ancestor_keys() for n in chain(asset_granted_nodes, granted_nodes)}
    ancestors_map = {node.key: node for node in
                     Node.objects.filter(key__in=chain(*ancestor_keys_map.values()))}
    for (node, _), keys in ancestor_keys_map:
        for key in keys:
            ancestor = ancestors_map[key]  # TODO 404
            inc_granted_count(ancestor, node._granted_count)
    keys = ancestors_map.keys() | {n.key for n in ancestor_keys_map.keys()}
    # 资产授权节点和直接授权节点，两者会有重叠
    all_nodes = [*granted_nodes, *asset_granted_nodes]

    for user in users:
        # 每个用户单独处理自己的树
        to_create = {}
        to_update = []
        _granted_nodes = GrantedNode.objects.filter(key__in=keys, user=user)
        granted_nodes_map = {gn.key: gn for gn in _granted_nodes}
        for node in all_nodes:
            _granted = getattr(node, '_granted', False),
            _asset_granted_count = getattr(node, '_asset_granted_count', 0)
            _granted_count = getattr(node, '_granted_count')
            if node.key in granted_nodes_map:
                granted_node = granted_nodes_map[node.key]
                if action is ADD:
                    if _granted:
                        if granted_node.granted:
                            #相同节点不能授权两次
                            raise ValueError('')
                        granted_node.granted = True

                    inc_asset_granted_count(granted_node, _asset_granted_count)
                    inc_granted_count(granted_node, _granted_count)
                elif action is REMOVE:
                    if _granted:
                        if not granted_node.granted:
                            # 数据有问题
                            raise ValueError('')
                        granted_node.granted = False
                    inc_asset_granted_count(granted_node, -_asset_granted_count)
                    inc_granted_count(granted_node, -_granted_count)

                to_update.append(granted_node)
            else:
                if action is REMOVE:
                    # 数据有问题
                    raise ValueError('')
                if node.key not in to_create:
                    granted_node = GrantedNode(
                        key=node.key,
                        user=user,
                        granted=_granted,
                        granted_count=_granted_count,
                        asset_granted_count=_asset_granted_count
                    )
                    to_create[node.key] = granted_node
                else:
                    granted_node = to_create[node.key]
                    granted_node.granted_count += _granted_count
                    granted_node.asset_granted_count += _asset_granted_count
                    if _granted:
                        if granted_node.granted:
                            raise ValueError()
                        granted_node.granted = True

        for gn in to_update:
            gn.granted_count = F('granted_count') + gn._granted_count
            gn.asset_granted_count = F('asset_granted_count') + gn._asset_granted_count
        GrantedNode.objects.bulk_update(to_update)
        GrantedNode.objects.bulk_create(to_create.values())
