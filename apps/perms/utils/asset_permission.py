# coding: utf-8

import re
from collections import defaultdict
from functools import reduce

from django.db.models import Q

from orgs.utils import set_to_root_org
from common.utils import get_logger, timeit
from common.tree import TreeNode
from assets.utils import TreeService
from ..models import AssetPermission
from ..hands import Node, Asset, SystemUser

logger = get_logger(__file__)


__all__ = [
    'is_obj_attr_has', 'sort_assets',
    'ParserNode', 'AssetPermissionUtilV2',
]


def get_user_permissions(user, include_group=True):
    if include_group:
        groups = user.groups.all()
        arg = Q(users=user) | Q(user_groups__in=groups)
    else:
        arg = Q(users=user)
    return AssetPermission.get_queryset_with_prefetch().filter(arg)


def get_user_group_permissions(user_group):
    return AssetPermission.get_queryset_with_prefetch().filter(
        user_groups=user_group
    )


def get_asset_permissions(asset, include_node=True):
    if include_node:
        nodes = asset.get_all_nodes(flat=True)
        arg = Q(assets=asset) | Q(nodes__in=nodes)
    else:
        arg = Q(assets=asset)
    return AssetPermission.objects.valid().filter(arg)


def get_node_permissions(node):
    return AssetPermission.objects.valid().filter(nodes=node)


def get_system_user_permissions(system_user):
    return AssetPermission.objects.valid().filter(
        system_users=system_user
    )


class AssetPermissionUtilV2:
    get_permissions_map = {
        "User": get_user_permissions,
        "UserGroup": get_user_group_permissions,
        "Asset": get_asset_permissions,
        "Node": get_node_permissions,
        "SystemUser": get_system_user_permissions,
    }
    assets_only = (
        'id', 'hostname', 'ip', "platform", "domain_id",
        'comment', 'is_active', 'os', 'org_id'
    )

    def __init__(self, obj, cache_policy='0'):
        self.object = obj
        self.obj_id = str(obj.id)
        self._permissions = None
        self._permissions_id = None  # 标记_permission的唯一值
        self._assets = None
        self._filter_id = 'None'  # 当通过filter更改 permission是标记
        self.change_org_if_need()
        self.nodes = None
        self._nodes = None
        self._assets_direct = None
        self._nodes_direct = None
        self._user_tree = None
        self.full_tree = Node.tree()

    @staticmethod
    def change_org_if_need():
        set_to_root_org()

    @property
    def permissions(self):
        if self._permissions:
            return self._permissions
        object_cls = self.object.__class__.__name__
        func = self.get_permissions_map[object_cls]
        permissions = func(self.object)
        self._permissions = permissions
        return permissions

    @timeit
    def filter_permissions(self, **filters):
        self._permissions = self.permissions.filter(**filters)

    @property
    def user_tree(self):
        return self.get_user_tree()

    @timeit
    def get_assets_direct(self):
        """
        返回直接授权的资产，
        并添加到tree.assets中
        :return:
        {asset.id: {system_user.id: actions, }, }
        """
        assets_ids = self.permissions.values_list('assets', flat=True)
        return Asset.objects.filter(id__in=assets_ids)

    @timeit
    def get_nodes_direct(self):
        """
        返回直接授权的节点，
        并将节点添加到tree.nodes中，并将节点下的资产添加到tree.assets中
        :return:
        {node.key: {system_user.id: actions,}, }
        """
        nodes_ids = self.permissions.values_list('nodes', flat=True)
        return Node.objects.filter(id__in=nodes_ids)

    @timeit
    def add_direct_nodes_to_user_tree(self, user_tree):
        nodes_direct_keys = self.permissions \
            .exclude(nodes__isnull=True) \
            .values_list('nodes__key', flat=True) \
            .distinct()
        nodes_direct_keys = list(nodes_direct_keys)
        # 排序，保证从上层节点开始加
        nodes_direct_keys.sort(key=lambda x: len(x))
        for key in nodes_direct_keys:
            # 如果树上已经有这个节点，代表子树已经存在
            if user_tree.contains(key):
                continue
            # 找到这个节点的父节点，如果父节点不在树上，则挂到ROOT上
            parent = self.full_tree.parent(key)
            if not user_tree.contains(parent.identifier):
                parent = user_tree.root_node()
            subtree = self.full_tree.subtree(key)
            user_tree.paste(parent.identifier, subtree, deep=True)

        for node in user_tree.all_nodes_itr():
            assets = list(self.full_tree.assets(node.identifier))
            user_tree.set_assets(node.identifier, assets)

    @timeit
    def add_single_assets_node_to_user_tree(self, user_tree):
        # 添加单独授权资产的节点
        nodes_single_assets = defaultdict(set)
        queryset = self.permissions.exclude(assets__isnull=True) \
            .values_list('assets', 'assets__nodes__key') \
            .distinct()

        for item in queryset:
            nodes_single_assets[item[1]].add(item[0])
        # Todo: 游离资产
        nodes_single_assets.pop(None, None)

        for key in tuple(nodes_single_assets.keys()):
            if user_tree.contains(key):
                nodes_single_assets.pop(key)

        # 获取单独授权资产，并没有在授权的节点上
        for key, assets in nodes_single_assets.items():
            node = self.full_tree.get_node(key, deep=True)
            parent_id = self.full_tree.parent(key).identifier
            parent = user_tree.get_node(parent_id)
            if not parent:
                parent = user_tree.root_node()
            user_tree.add_node(node, parent)
            user_tree.set_assets(node.identifier, assets)

    @timeit
    def parse_user_tree_to_full_tree(self, user_tree):
        # 开始修正user_tree，保证父节点都在树上
        root_children = user_tree.children('')
        for child in root_children:
            if child.identifier.isdigit():
                continue
            ancestors = self.full_tree.ancestors(
                child.identifier, with_self=False, deep=True
            )
            if not ancestors:
                continue
            parent_id = ancestors[0].identifier
            user_tree.safe_add_ancestors(ancestors)
            user_tree.move_node(child.identifier, parent_id)

    @timeit
    def get_user_tree(self):
        if self._user_tree:
            return self._user_tree
        user_tree = TreeService()
        full_tree_root = self.full_tree.root_node()
        user_tree.create_node(
            tag=full_tree_root.tag,
            identifier=full_tree_root.identifier
        )
        self.add_direct_nodes_to_user_tree(user_tree)
        self.add_single_assets_node_to_user_tree(user_tree)
        self.parse_user_tree_to_full_tree(user_tree)
        self._user_tree = user_tree
        return user_tree

    # Todo: 是否可以获取多个资产的系统用户
    def get_asset_system_users_with_actions(self, asset):
        nodes = asset.get_nodes()
        nodes_keys_related = set()
        for node in nodes:
            ancestor_keys = node.get_ancestor_keys(with_self=True)
            nodes_keys_related.update(set(ancestor_keys))
        pattern = []
        for key in nodes_keys_related:
            pattern.append(r'^{0}$|^{0}:'.format(key))
        pattern = '|'.join(list(pattern))
        kwargs = {"assets": asset}

        if pattern:
            kwargs["nodes__key__regex"] = pattern

        queryset = self.permissions
        if len(kwargs) == 1:
            queryset = queryset.filter(**kwargs)
        elif len(kwargs) > 1:
            kwargs = [{k: v} for k, v in kwargs.items()]
            args = [Q(**kw) for kw in kwargs]
            args = reduce(lambda x, y: x | y, args)
            queryset = queryset.filter(args)
        else:
            queryset = queryset.none()
        queryset = queryset.distinct().prefetch_related('system_users')
        system_users_actions = defaultdict(int)
        for perm in queryset:
            system_users = perm.system_users.all()
            if not system_users or not perm.actions:
                continue
            for s in system_users:
                if not asset.has_protocol(s.protocol):
                    continue
                system_users_actions[s] |= perm.actions
        return system_users_actions

    def get_permissions_nodes_and_assets(self):
        permissions = self.permissions.values_list('assets', 'nodes__key').distinct()
        nodes_keys = set()
        assets_ids = set()
        for asset_id, node_key in permissions:
            if asset_id:
                assets_ids.add(asset_id)
            if node_key:
                nodes_keys.add(node_key)
        nodes_keys = self.clean_nodes_keys(nodes_keys)
        return nodes_keys, assets_ids

    @staticmethod
    def filter_assets_by_or_kwargs(kwargs):
        if len(kwargs) == 1:
            queryset = Asset.objects.filter(**kwargs)
        elif len(kwargs) > 1:
            kwargs = [{k: v} for k, v in kwargs.items()]
            args = [Q(**kw) for kw in kwargs]
            args = reduce(lambda x, y: x | y, args)
            queryset = Asset.objects.filter(args)
        else:
            queryset = Asset.objects.none()
        return queryset

    @timeit
    def get_assets(self):
        nodes_keys, assets_ids = self.get_permissions_nodes_and_assets()
        pattern = set()
        for key in nodes_keys:
            pattern.add(r'^{0}$|^{0}:'.format(key))
        pattern = '|'.join(list(pattern))
        kwargs = {}
        if assets_ids:
            kwargs["id__in"] = assets_ids
        if pattern:
            kwargs["nodes__key__regex"] = pattern
        queryset = self.filter_assets_by_or_kwargs(kwargs)
        return queryset.valid().distinct()

    def get_nodes_assets(self, node, deep=False):
        if deep:
            assets_ids = self.user_tree.all_assets(node.key)
        else:
            assets_ids = self.user_tree.assets(node.key)
        queryset = Asset.objects.filter(id__in=assets_ids)
        return queryset.valid().distinct()

    @staticmethod
    def clean_nodes_keys(nodes_keys):
        nodes_keys = sorted(list(nodes_keys), key=lambda x: (len(x), x))
        nodes_keys_clean = []
        for key in nodes_keys[::-1]:
            found = False
            for k in nodes_keys:
                if key.startswith(k + ':'):
                    found = True
                    break
            if not found:
                nodes_keys_clean.append(key)
        return nodes_keys_clean

    def get_nodes(self):
        return [n.identifier for n in self.user_tree.all_nodes_itr()]

    def get_system_users(self):
        system_users_id = self.permissions.values_list('system_users', flat=True).distinct()
        return SystemUser.objects.filter(id__in=system_users_id)


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


class ParserNode:
    nodes_only_fields = ("key", "value", "id")
    assets_only_fields = ("platform", "hostname", "id", "ip", "protocols")
    system_users_only_fields = (
        "id", "name", "username", "protocol", "priority", "login_mode",
    )

    @staticmethod
    def parse_node_to_tree_node(node):
        name = '{} ({})'.format(node.value, node.assets_amount)
        # name = node.value
        data = {
            'id': node.key,
            'name': name,
            'title': name,
            'pId': node.parent_key,
            'isParent': True,
            'open': node.is_root(),
            'meta': {
                'node': {
                    "id": node.id,
                    "key": node.key,
                    "value": node.value,
                },
                'type': 'node'
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    @staticmethod
    def parse_asset_to_tree_node(node, asset):
        icon_skin = 'file'
        if asset.platform.lower() == 'windows':
            icon_skin = 'windows'
        elif asset.platform.lower() == 'linux':
            icon_skin = 'linux'
        data = {
            'id': str(asset.id),
            'name': asset.hostname,
            'title': asset.ip,
            'pId': node.key,
            'isParent': False,
            'open': False,
            'iconSkin': icon_skin,
            'meta': {
                'type': 'asset',
                'asset': {
                    'id': asset.id,
                    'hostname': asset.hostname,
                    'ip': asset.ip,
                    'protocols': asset.protocols_as_list,
                    'platform': asset.platform,
                },
            }
        }
        tree_node = TreeNode(**data)
        return tree_node
