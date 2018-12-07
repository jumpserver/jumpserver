# coding: utf-8

from __future__ import absolute_import, unicode_literals
from collections import defaultdict
from django.db.models import Q

from common.utils import get_logger
from .models import AssetPermission
from .hands import Node

logger = get_logger(__file__)


class GenerateTree:
    def __init__(self):
        """
        nodes: {"node_instance": {
            "asset_instance": set("system_user")
        }
        """
        self.__all_nodes = Node.objects.all()
        self.__node_asset_map = defaultdict(set)
        self.nodes = defaultdict(dict)

    def add_asset(self, asset, system_users):
        nodes = asset.nodes.all()
        self.add_nodes(nodes)
        for node in nodes:
            self.nodes[node][asset].update(system_users)

    def get_nodes(self):
        for node in self.nodes:
            assets = set(self.nodes.get(node).keys())
            for n in self.nodes.keys():
                if n.key.startswith(node.key + ':'):
                    assets.update(set(self.nodes[n].keys()))
            node.assets_amount = len(assets)
        return self.nodes

    def add_node(self, node):
        if node in self.nodes:
            return
        else:
            self.nodes[node] = defaultdict(set)
        if node.is_root():
            return
        for n in self.__all_nodes:
            if n.key == node.parent_key:
                self.add_node(n)
                break

    def add_nodes(self, nodes):
        for node in nodes:
            self.add_node(node)


def get_user_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups__in=groups)
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
        arg = Q(assets=asset) | Q(nodes__in=nodes)
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
        self._assets = None

    @property
    def permissions(self):
        if self._permissions:
            return self._permissions
        object_cls = self.object.__class__.__name__
        func = self.get_permissions_map[object_cls]
        permissions = func(self.object)
        self._permissions = permissions
        return permissions

    def filter_permission_with_system_user(self, system_user):
        self._permissions = self.permissions.filter(system_users=system_user)

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
        if self._assets:
            return self._assets
        assets = self.get_assets_direct()
        nodes = self.get_nodes_direct()
        for node, system_users in nodes.items():
            _assets = node.get_all_assets().valid().prefetch_related('nodes')
            for asset in _assets:
                assets[asset].update(system_users)
        self._assets = assets
        return self._assets

    def get_nodes_with_assets(self):
        """
        返回节点并且包含资产
        {"node": {"assets": set("system_user")}}
        :return:
        """
        assets = self.get_assets()
        tree = GenerateTree()
        for asset, system_users in assets.items():
            tree.add_asset(asset, system_users)
        return tree.get_nodes()

    def get_system_users(self):
        system_users = set()
        permissions = self.permissions.prefetch_related('system_users')
        for perm in permissions:
            system_users.update(perm.system_users.all())
        return system_users


def is_obj_attr_has(obj, val, attrs=("hostname", "ip", "comment")):
    if not attrs:
        vals = [val for val in obj.__dict__.values() if isinstance(val, (str, int))]
    else:
        vals = [getattr(obj, attr) for attr in attrs if
                hasattr(obj, attr) and isinstance(hasattr(obj, attr), (str, int))]

    for v in vals:
        if str(v).find(val) != -1:
            return True
    return False


def sort_assets(assets, order_by='hostname', reverse=False):
    if order_by == 'ip':
        assets = sorted(assets, key=lambda asset: [int(d) for d in asset.ip.split('.') if d.isdigit()], reverse=reverse)
    else:
        assets = sorted(assets, key=lambda asset: getattr(asset, order_by), reverse=reverse)
    return assets
