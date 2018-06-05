# coding: utf-8

from __future__ import absolute_import, unicode_literals
from collections import defaultdict
from django.db.models import Q

from common.utils import get_logger
from .models import AssetPermission
from .hands import Node

logger = get_logger(__file__)


def get_user_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups=groups)
    else:
        arg = Q(users=user)
    return AssetPermission.objects.all().valid().filter(arg)


def get_user_group_permissions(user_group):
    return AssetPermission.objects.all().valid().filter(
        user_groups=user_group
    )


def get_asset_permissions(asset, include_node=True):
    if include_node:
        nodes = asset.get_all_nodes(flat=True)
        arg = Q(assets=asset) | Q(nodes=nodes)
    else:
        arg = Q(assets=asset)
    return AssetPermission.objects.all().valid().filter(arg)


def get_node_permissions(node):
    return AssetPermission.objects.all().valid().filter(nodes=node)


def get_system_user_permissions(system_user):
    return AssetPermission.objects.valid().all().filter(
        system_users=system_user
    )


class AssetPermissionUtil:
    get_permissions_map = {
        "User": get_user_permissions,
        "UserGroup": get_user_group_permissions,
        "Asset": get_asset_permissions,
        "Node": get_node_permissions,
        "SystemUser": get_node_permissions,
    }

    def __init__(self, obj):
        self.object = obj
        self._permissions = None

    @property
    def permissions(self):
        if self._permissions:
            return self._permissions
        object_cls = self.object.__class__.__name__
        func = self.get_permissions_map[object_cls]
        permissions = func(self.object)
        self._permissions = permissions
        return permissions

    def get_nodes_direct(self):
        """
        返回用户/组授权规则直接关联的节点
        :return: {node1: set(system_user1,)}
        """
        nodes = defaultdict(set)
        permissions = self.permissions.prefetch_related('nodes', 'system_users')
        for perm in permissions:
            for node in perm.nodes.all():
                nodes[node].update(perm.system_users.all())
        return nodes

    def get_assets_direct(self):
        """
        返回用户授权规则直接关联的资产
        :return: {asset1: set(system_user1,)}
        """
        assets = defaultdict(set)
        permissions = self.permissions.prefetch_related('assets', 'system_users')
        for perm in permissions:
            for asset in perm.assets.all().valid().prefetch_related('nodes'):
                assets[asset].update(perm.system_users.all())
        return assets

    def get_assets(self):
        assets = self.get_assets_direct()
        nodes = self.get_nodes_direct()
        for node, system_users in nodes.items():
            _assets = node.get_all_assets().valid().prefetch_related('nodes')
            for asset in _assets:
                if isinstance(asset, Node):
                    print(_assets)
                assets[asset].update(system_users)
        return assets

    def get_nodes_with_assets(self):
        """
        返回节点并且包含资产
        {"node": {"assets": set("system_user")}}
        :return:
        """
        assets = self.get_assets()
        nodes = defaultdict(dict)
        for asset, system_users in assets.items():
            _nodes = asset.nodes.all()
            for node in _nodes:
                if asset in nodes[node]:
                    nodes[node][asset].update(system_users)
                else:
                    nodes[node][asset] = system_users
        return nodes


