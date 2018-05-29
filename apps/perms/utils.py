# coding: utf-8

from __future__ import absolute_import, unicode_literals
import collections
from collections import defaultdict
from django.utils import timezone
import copy

from common.utils import set_or_append_attr_bulk, get_logger
from .models import AssetPermission
from .hands import Node

logger = get_logger(__file__)


class Tree:
    def __init__(self):
        self.__all_nodes = list(Node.objects.all())
        self.__node_asset_map = defaultdict(set)
        self.nodes = defaultdict(dict)
        self.root = Node.root()
        self.init_node_asset_map()

    def init_node_asset_map(self):
        for node in self.__all_nodes:
            assets = node.get_assets().values_list('id', flat=True)
            for asset in assets:
                self.__node_asset_map[str(asset)].add(node)

    def add_asset(self, asset, system_users):
        nodes = self.__node_asset_map.get(str(asset.id), [])
        self.add_nodes(nodes)
        for node in nodes:
            self.nodes[node][asset].update(system_users)

    def add_node(self, node):
        if node in self.nodes:
            return
        else:
            self.nodes[node] = defaultdict(set)
        if node.key == self.root.key:
            return
        parent_key = ':'.join(node.key.split(':')[:-1])
        for n in self.__all_nodes:
            if n.key == parent_key:
                self.add_node(n)
                break

    def add_nodes(self, nodes):
        for node in nodes:
            self.add_node(node)


class AssetPermissionUtil:
    @staticmethod
    def get_user_permissions(user):
        return AssetPermission.objects.all().valid().filter(users=user)

    @staticmethod
    def get_user_group_permissions(user_group):
        return AssetPermission.objects.all().valid().filter(
            user_groups=user_group
        )

    @staticmethod
    def get_asset_permissions(asset):
        return AssetPermission.objects.all().valid().filter(
            assets=asset
        )

    @staticmethod
    def get_node_permissions(node):
        return AssetPermission.objects.all().valid().filter(nodes=node)

    @staticmethod
    def get_system_user_permissions(system_user):
        return AssetPermission.objects.valid().all().filter(
            system_users=system_user
        )

    @classmethod
    def get_user_group_nodes(cls, group):
        nodes = defaultdict(set)
        permissions = cls.get_user_group_permissions(group)
        for perm in permissions:
            _nodes = perm.nodes.all()
            _system_users = perm.system_users.all()
            set_or_append_attr_bulk(_nodes, 'permission', perm.id)
            for node in _nodes:
                nodes[node].update(set(_system_users))
        return nodes

    @classmethod
    def get_user_group_assets_direct(cls, group):
        assets = defaultdict(set)
        permissions = cls.get_user_group_permissions(group)
        for perm in permissions:
            _assets = perm.assets.all().valid()
            _system_users = perm.system_users.all()
            set_or_append_attr_bulk(_assets, 'permission', perm.id)
            for asset in _assets:
                assets[asset].update(set(_system_users))
        return assets

    @classmethod
    def get_user_group_nodes_assets(cls, group):
        assets = defaultdict(set)
        nodes = cls.get_user_group_nodes(group)
        for node, _system_users in nodes.items():
            _assets = node.get_all_valid_assets()
            set_or_append_attr_bulk(_assets, 'inherit_node', node.id)
            set_or_append_attr_bulk(_assets, 'permission', getattr(node, 'permission', None))
            for asset in _assets:
                assets[asset].update(set(_system_users))
        return assets

    @classmethod
    def get_user_group_assets(cls, group):
        assets = defaultdict(set)
        _assets = cls.get_user_group_assets_direct(group)
        _nodes_assets = cls.get_user_group_nodes_assets(group)
        for asset, _system_users in _assets.items():
            assets[asset].update(set(_system_users))
        for asset, _system_users in _nodes_assets.items():
            assets[asset].update(set(_system_users))
        return assets

    @classmethod
    def get_user_group_nodes_with_assets(cls, group):
        """
        :param group:
        :return: {node: {asset: set(su1, su2)}}
        """
        _assets = cls.get_user_group_assets(group)
        tree = Tree()
        for asset, _system_users in _assets.items():
            _nodes = asset.get_nodes()
            tree.add_nodes(_nodes)
            for node in _nodes:
                tree.nodes[node][asset].update(_system_users)
        return tree.nodes

    @classmethod
    def get_user_assets_direct(cls, user):
        assets = defaultdict(set)
        permissions = list(cls.get_user_permissions(user))
        for perm in permissions:
            _assets = perm.assets.all().valid()
            _system_users = perm.system_users.all()
            set_or_append_attr_bulk(_assets, 'permission', perm.id)
            for asset in _assets:
                assets[asset].update(set(_system_users))
        return assets

    @classmethod
    def get_user_nodes_direct(cls, user):
        nodes = defaultdict(set)
        permissions = cls.get_user_permissions(user)
        for perm in permissions:
            _nodes = perm.nodes.all()
            _system_users = perm.system_users.all()
            set_or_append_attr_bulk(_nodes, 'permission', perm.id)
            for node in _nodes:
                nodes[node].update(set(_system_users))
        return nodes

    @classmethod
    def get_user_nodes_inherit_group(cls, user):
        nodes = defaultdict(set)
        groups = user.groups.all()
        for group in groups:
            _nodes = cls.get_user_group_nodes(group)
            for node, system_users in _nodes.items():
                nodes[node].update(set(system_users))
        return nodes

    @classmethod
    def get_user_nodes(cls, user):
        nodes = cls.get_user_nodes_direct(user)
        nodes_inherit = cls.get_user_nodes_inherit_group(user)
        for node, system_users in nodes_inherit.items():
            nodes[node].update(set(system_users))
        return nodes

    @classmethod
    def get_user_nodes_assets_direct(cls, user):
        assets = defaultdict(set)
        nodes = cls.get_user_nodes_direct(user)
        for node, _system_users in nodes.items():
            _assets = node.get_all_valid_assets()
            set_or_append_attr_bulk(_assets, 'inherit_node', node.id)
            set_or_append_attr_bulk(_assets, 'permission', getattr(node, 'permission', None))
            for asset in _assets:
                assets[asset].update(set(_system_users))
        return assets

    @classmethod
    def get_user_assets_inherit_group(cls, user):
        assets = defaultdict(set)
        for group in user.groups.all():
            _assets = cls.get_user_group_assets(group)
            set_or_append_attr_bulk(_assets, 'inherit_group', group.id)
            for asset, _system_users in _assets.items():
                assets[asset].update(_system_users)
        return assets

    @classmethod
    def get_user_assets(cls, user):
        assets = defaultdict(set)
        _assets_direct = cls.get_user_assets_direct(user)
        _nodes_assets_direct = cls.get_user_nodes_assets_direct(user)
        _assets_inherit_group = cls.get_user_assets_inherit_group(user)
        for asset, _system_users in _assets_direct.items():
            assets[asset].update(_system_users)
        for asset, _system_users in _nodes_assets_direct.items():
            assets[asset].update(_system_users)
        for asset, _system_users in _assets_inherit_group.items():
            assets[asset].update(_system_users)
        return assets

    @classmethod
    def get_user_nodes_with_assets(cls, user):
        """
        :param user:
        :return: {node: {asset: set(su1, su2)}}
        """
        tree = Tree()
        _assets = cls.get_user_assets(user)
        for asset, _system_users in _assets.items():
            tree.add_asset(asset, _system_users)
            # _nodes = asset.get_nodes()
            # tree.add_nodes(_nodes)
            # for node in _nodes:
            #     tree.nodes[node][asset].update(_system_users)
        return tree.nodes

    @classmethod
    def get_system_user_assets(cls, system_user):
        assets = set()
        permissions = cls.get_system_user_permissions(system_user)
        for perm in permissions:
            assets.update(set(perm.assets.all().valid()))
            nodes = perm.nodes.all()
            for node in nodes:
                assets.update(set(node.get_all_valid_assets()))
        return assets

    @classmethod
    def get_node_system_users(cls, node):
        system_users = set()
        permissions = cls.get_node_permissions(node)
        for perm in permissions:
            system_users.update(perm.system_users.all())
        return system_users


# Abandon
class NodePermissionUtil:
    """

    """

    @staticmethod
    def get_user_group_permissions(user_group):
        return user_group.nodepermission_set.all() \
            .filter(is_active=True) \
            .filter(date_expired__gt=timezone.now())

    @staticmethod
    def get_system_user_permissions(system_user):
        return system_user.nodepermission_set.all() \
            .filter(is_active=True) \
            .filter(date_expired__gt=timezone.now())

    @classmethod
    def get_user_group_nodes(cls, user_group):
        """
        获取用户组授权的node和系统用户
        :param user_group:
        :return: {"node": set(systemuser1, systemuser2), ..}
        """
        permissions = cls.get_user_group_permissions(user_group)
        nodes_directed = collections.defaultdict(set)

        for perm in permissions:
            nodes_directed[perm.node].add(perm.system_user)

        nodes = copy.deepcopy(nodes_directed)
        for node, system_users in nodes_directed.items():
            for child in node.get_all_children_with_self():
                nodes[child].update(system_users)
        return nodes

    @classmethod
    def get_user_group_nodes_with_assets(cls, user_group):
        """
        获取用户组授权的节点和系统用户，节点下带有资产
        :param user_group:
        :return: {"node": {"assets": "", "system_user": ""}, {}}
        """
        nodes = cls.get_user_group_nodes(user_group)
        nodes_with_assets = dict()
        for node, system_users in nodes.items():
            nodes_with_assets[node] = {
                'assets': node.get_valid_assets(),
                'system_users': system_users
            }
        return nodes_with_assets

    @classmethod
    def get_user_group_assets(cls, user_group):
        assets = collections.defaultdict(set)
        permissions = cls.get_user_group_permissions(user_group)

        for perm in permissions:
            for asset in perm.node.get_all_assets():
                assets[asset].add(perm.system_user)
        return assets

    @classmethod
    def get_user_nodes(cls, user):
        nodes = collections.defaultdict(set)
        groups = user.groups.all()
        for group in groups:
            group_nodes = cls.get_user_group_nodes(group)
            for node, system_users in group_nodes.items():
                nodes[node].update(system_users)
        return nodes

    @classmethod
    def get_user_nodes_with_assets(cls, user):
        nodes = cls.get_user_nodes(user)
        nodes_with_assets = dict()
        for node, system_users in nodes.items():
            nodes_with_assets[node] = {
                'assets': node.get_valid_assets(),
                'system_users': system_users
            }
        return nodes_with_assets

    @classmethod
    def get_user_assets(cls, user):
        assets = collections.defaultdict(set)
        nodes_with_assets = cls.get_user_nodes_with_assets(user)

        for v in nodes_with_assets.values():
            for asset in v['assets']:
                assets[asset].update(v['system_users'])
        return assets

    @classmethod
    def get_system_user_assets(cls, system_user):
        assets = set()
        permissions = cls.get_system_user_permissions(system_user)

        for perm in permissions:
            assets.update(perm.node.get_all_assets())
        return assets

