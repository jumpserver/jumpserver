# coding: utf-8

from __future__ import absolute_import, unicode_literals
import uuid
from collections import defaultdict
import json
from hashlib import md5

from django.utils import timezone
from django.db.models import Q
from django.core.cache import cache
from django.conf import settings

from common.utils import get_logger
from common.tree import TreeNode
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
        self.__all_nodes = list(Node.objects.all())
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

    CACHE_KEY_PREFIX = '_ASSET_PERM_CACHE_'
    CACHE_META_KEY_PREFIX = '_ASSET_PERM_META_KEY_'
    CACHE_TIME = settings.ASSETS_PERM_CACHE_TIME
    CACHE_POLICY_MAP = (('0', 'never'), ('1', 'using'), ('2', 'refresh'))

    def __init__(self, obj, cache_policy='0'):
        self.object = obj
        self.obj_id = str(obj.id)
        self._permissions = None
        self._permissions_id = None  # 标记_permission的唯一值
        self._assets = None
        self._filter_id = 'None'  # 当通过filter更改 permission是标记
        self.cache_policy = cache_policy

    @classmethod
    def is_not_using_cache(cls, cache_policy):
        return cls.CACHE_TIME == 0 or cache_policy in cls.CACHE_POLICY_MAP[0]

    @classmethod
    def is_using_cache(cls, cache_policy):
        return cls.CACHE_TIME != 0 and cache_policy in cls.CACHE_POLICY_MAP[1]

    @classmethod
    def is_refresh_cache(cls, cache_policy):
        return cache_policy in cls.CACHE_POLICY_MAP[2]

    def _is_not_using_cache(self):
        return self.is_not_using_cache(self.cache_policy)

    def _is_using_cache(self):
        return self.is_using_cache(self.cache_policy)

    def _is_refresh_cache(self):
        return self.is_refresh_cache(self.cache_policy)

    @property
    def permissions(self):
        if self._permissions:
            return self._permissions
        object_cls = self.object.__class__.__name__
        func = self.get_permissions_map[object_cls]
        permissions = func(self.object)
        self._permissions = permissions
        return permissions

    def filter_permissions(self, **filters):
        filters_json = json.dumps(filters, sort_keys=True)
        self._permissions = self.permissions.filter(**filters)
        self._filter_id = md5(filters_json.encode()).hexdigest()

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
                assets[asset].update(
                    perm.system_users.filter(protocol=asset.protocol)
                )
        return assets

    def get_assets_without_cache(self):
        if self._assets:
            return self._assets
        assets = self.get_assets_direct()
        nodes = self.get_nodes_direct()
        for node, system_users in nodes.items():
            _assets = node.get_all_assets().valid().prefetch_related('nodes')
            for asset in _assets:
                assets[asset].update(
                    [s for s in system_users if s.protocol == asset.protocol]
                )
        self._assets = assets
        return self._assets

    def get_cache_key(self, resource):
        cache_key = self.CACHE_KEY_PREFIX + '{obj_id}_{filter_id}_{resource}'
        return cache_key.format(
            obj_id=self.obj_id, filter_id=self._filter_id,
            resource=resource
        )

    @property
    def node_key(self):
        return self.get_cache_key('NODES_WITH_ASSETS')

    @property
    def asset_key(self):
        return self.get_cache_key('ASSETS')

    @property
    def system_key(self):
        return self.get_cache_key('SYSTEM_USER')

    def get_assets_from_cache(self):
        cached = cache.get(self.asset_key)
        if not cached:
            self.update_cache()
            cached = cache.get(self.asset_key)
        return cached

    def get_assets(self):
        if self._is_not_using_cache():
            return self.get_assets_from_cache()
        elif self._is_refresh_cache():
            self.expire_cache()
            return self.get_assets_from_cache()
        else:
            self.expire_cache()
            return self.get_assets_without_cache()

    def get_nodes_with_assets_without_cache(self):
        """
        返回节点并且包含资产
        {"node": {"assets": set("system_user")}}
        :return:
        """
        assets = self.get_assets_without_cache()
        tree = GenerateTree()
        for asset, system_users in assets.items():
            tree.add_asset(asset, system_users)
        return tree.get_nodes()

    def get_nodes_with_assets_from_cache(self):
        cached = cache.get(self.node_key)
        if not cached:
            self.update_cache()
            cached = cache.get(self.node_key)
        return cached

    def get_nodes_with_assets(self):
        if self._is_using_cache():
            return self.get_nodes_with_assets_from_cache()
        elif self._is_refresh_cache():
            self.expire_cache()
            return self.get_nodes_with_assets_from_cache()
        else:
            return self.get_nodes_with_assets_without_cache()

    def get_system_user_without_cache(self):
        system_users = set()
        permissions = self.permissions.prefetch_related('system_users')
        for perm in permissions:
            system_users.update(perm.system_users.all())
        return system_users

    def get_system_user_from_cache(self):
        cached = cache.get(self.system_key)
        if not cached:
            self.update_cache()
            cached = cache.get(self.system_key)
        return cached

    def get_system_users(self):
        if self._is_using_cache():
            return self.get_system_user_from_cache()
        elif self._is_refresh_cache():
            self.expire_cache()
            return self.get_system_user_from_cache()
        else:
            return self.get_system_user_without_cache()

    def get_meta_cache_key(self):
        cache_key = self.CACHE_META_KEY_PREFIX + '{obj_id}_{filter_id}'
        key = cache_key.format(
            obj_id=str(self.object.id), filter_id=self._filter_id
        )
        return key

    @property
    def cache_meta(self):
        key = self.get_meta_cache_key()
        return cache.get(key) or {}

    def set_meta_to_cache(self):
        key = self.get_meta_cache_key()
        meta = {
            'id': str(uuid.uuid4()),
            'datetime': timezone.now(),
            'object': str(self.object)
        }
        cache.set(key, meta, self.CACHE_TIME)

    def expire_cache_meta(self):
        cache_key = self.CACHE_META_KEY_PREFIX + '{obj_id}_*'
        key = cache_key.format(obj_id=str(self.object.id))
        cache.delete_pattern(key)

    def update_cache(self):
        assets = self.get_assets_without_cache()
        nodes = self.get_nodes_with_assets_without_cache()
        system_users = self.get_system_user_without_cache()
        cache.set(self.asset_key, assets, self.CACHE_TIME)
        cache.set(self.node_key, nodes, self.CACHE_TIME)
        cache.set(self.system_key, system_users, self.CACHE_TIME)
        self.set_meta_to_cache()

    def expire_cache(self):
        """
        因为 获取用户的节点，资产，系统用户等都能会缓存，这里会清理所有与该对象有关的
        缓存，以免造成不统一的情况
        :return:
        """
        cache_key = self.CACHE_KEY_PREFIX + '{obj_id}_*'
        key = cache_key.format(obj_id='*')
        cache.delete_pattern(key)
        self.expire_cache_meta()

    @classmethod
    def expire_all_cache_meta(cls):
        key = cls.CACHE_META_KEY_PREFIX + '*'
        cache.delete_pattern(key)

    @classmethod
    def expire_all_cache(cls):
        key = cls.CACHE_KEY_PREFIX + '*'
        cache.delete_pattern(key)


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


def parse_node_to_tree_node(node):
    from . import serializers
    name = '{} ({})'.format(node.value, node.assets_amount)
    node_serializer = serializers.GrantedNodeSerializer(node)
    data = {
        'id': node.key,
        'name': name,
        'title': name,
        'pId': node.parent_key,
        'isParent': True,
        'open': node.is_root(),
        'meta': {
            'node': node_serializer.data,
            'type': 'node'
        }
    }
    tree_node = TreeNode(**data)
    return tree_node


def parse_asset_to_tree_node(node, asset, system_users):
    system_users_protocol_matched = [s for s in system_users if s.protocol == asset.protocol]
    icon_skin = 'file'
    if asset.platform.lower() == 'windows':
        icon_skin = 'windows'
    elif asset.platform.lower() == 'linux':
        icon_skin = 'linux'
    system_users = []
    for system_user in system_users_protocol_matched:
        system_users.append({
            'id': system_user.id,
            'name': system_user.name,
            'username': system_user.username,
            'protocol': system_user.protocol,
            'priority': system_user.priority,
            'login_mode': system_user.login_mode,
            'comment': system_user.comment,
        })
    data = {
        'id': str(asset.id),
        'name': asset.hostname,
        'title': asset.ip,
        'pId': node.key,
        'isParent': False,
        'open': False,
        'iconSkin': icon_skin,
        'meta': {
            'system_users': system_users,
            'type': 'asset',
            'asset': {
                'id': asset.id,
                'hostname': asset.hostname,
                'ip': asset.ip,
                'port': asset.port,
                'protocol': asset.protocol,
                'platform': asset.platform,
                'domain': None if not asset.domain else asset.domain.id,
                'is_active': asset.is_active,
                'comment': asset.comment
            },
        }
    }
    tree_node = TreeNode(**data)
    return tree_node
