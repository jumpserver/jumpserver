#  coding: utf-8
#
import itertools
from collections import defaultdict

from django.db.models import Q
from django.conf import settings

from ..models import AssetPermission
from ..hands import Asset

# get permissions


class GetPermission:
    GET_PERMISSION_MAP = {
        "User": 'get_user_permissions',
        "UserGroup": 'get_user_group_permissions',
        "Asset": 'get_asset_permissions',
        "Node": 'get_node_permissions',
        "SystemUser": 'get_system_user_permissions',
    }

    def __init__(self, obj):
        self.object = obj

    def get_permissions(self):
        obj_class = self.object.__class__.__name__
        method = self.GET_PERMISSION_MAP[obj_class]
        return getattr(self, method)(self.object)

    @staticmethod
    def get_user_permissions(user, include_group=True):
        if include_group:
            groups = user.groups.all()
            arg = Q(users=user) | Q(user_groups__in=groups)
        else:
            arg = Q(users=user)
        return AssetPermission.get_queryset_with_prefetch().filter(arg)

    @staticmethod
    def get_user_group_permissions(user_group):
        return AssetPermission.get_queryset_with_prefetch().filter(
            user_groups=user_group
        )

    @staticmethod
    def get_asset_permissions(asset, include_node=True):
        if include_node:
            nodes = asset.get_all_nodes(flat=True)
            arg = Q(assets=asset) | Q(nodes__in=nodes)
        else:
            arg = Q(assets=asset)
        return AssetPermission.objects.valid().filter(arg)

    @staticmethod
    def get_node_permissions(node):
        return AssetPermission.objects.valid().filter(nodes=node)

    @staticmethod
    def get_system_user_permissions(system_user):
        return AssetPermission.objects.valid().filter(
            system_users=system_user
        )


# util


class CachePolicy:
    CACHE_TIME = settings.ASSETS_PERM_CACHE_TIME
    CACHE_POLICY_MAP = (('0', 'never'), ('1', 'using'), ('2', 'refresh'))

    def __init__(self, cache_policy):
        self._cache_policy = cache_policy or '0'

    @property
    def _cache_time_is_zero(self):
        return self.CACHE_TIME == 0

    @property
    def is_never_cache(self):
        return self._cache_policy in self.CACHE_POLICY_MAP[0] \
               or self._cache_time_is_zero

    @property
    def is_using_cache(self):
        return self._cache_policy in self.CACHE_POLICY_MAP[1] \
               and not self._cache_time_is_zero

    @property
    def is_refresh_cache(self):
        return self._cache_policy in self.CACHE_POLICY_MAP[2]


class GenerateTree:
    pass


class AssetPermissionCacheMixin:
    # cache

    def __init__(self, *args, **kwargs):
        cache_policy = kwargs.get('cache_policy', '0')
        self.cache_policy = CachePolicy(cache_policy)
        super().__init__(*args, **kwargs)

    def _get_assets_ids_from_cache(self):
        pass

    def _get_nodes_keys_from_cache(self):
        pass

    def _get_nodes_keys_with_assets_ids_from_cache(self):
        pass

    def _get_system_users_ids_from_cache(self):
        pass

    def _get_resource_from_cache(self, resource):
        method = '_get_{}_from_cache'.format(resource)
        return getattr(self, method)()


class AssetPermissionDBMixin:
    # db
    def __init__(self, *args, **kwargs):
        self.object = kwargs.get('instance')
        self._permissions = None
        super().__init__(*args, **kwargs)

    @property
    def permissions(self):
        if not self._permissions:
            self._permissions = GetPermission(self.object).get_permissions()
        return self._permissions

    def __get_direct_assets_ids_with_system_users_ids(self):
        assets_ids = defaultdict(lambda: defaultdict(int))
        for perm in self.permissions:
            _actions = perm.actions
            _assets_ids = perm.assets.all().valid().values_list('id', flat=True)
            _system_users_ids = perm.system_users.all().values_list('id', flat=True)
            _iterable = itertools.product(_assets_ids, _system_users_ids)
            for _asset_id, _system_user_id in _iterable:
                assets_ids[_asset_id][_system_user_id] = _actions
        return assets_ids

    def __get_direct_nodes_keys_with_system_users_ids(self):
        nodes_keys = defaultdict(lambda: defaultdict(int))
        for perm in self.permissions:
            _actions = perm.actions
            _nodes_keys = perm.nodes.all().values_list('key', flat=True)
            _system_users_ids = perm.system_users.all().values_list('id', flat=True)
            _iterable = itertools.product(_nodes_keys, _system_users_ids)
            for _node_key, _system_user_id in _iterable:
                nodes_keys[_node_key][_system_user_id] = _actions
        return nodes_keys

    def __get_direct_nodes_keys_with_sysetm_users_ids_and_add_to_tree(self):
        nodes_keys = self.__get_direct_nodes_keys_with_system_users_ids()
        self.tree.add_node(nodes_keys)

    def __get_assets_ids_direct_nodes(self):
        assets_ids = []
        nodes_keys = self.__get_nodes_keys_direct()
        _pattern = set()
        for _key in nodes_keys:
            _pattern.add(r'^{0}$|^{0}:'.format(_key))
        pattern = '|'.join(list(_pattern))
        if pattern:
            assets_ids = Asset.objects.filter(nodes__key__regex=pattern).\
                values_list('id', flat=True).distinct()
        return list(assets_ids)

    def _get_assets_ids_from_db(self):
        # assets_direct + assets_under_direct_nodes
        assets_ids = set()
        _assets_ids = self.__get_assets_ids_direct()
        _assets_ids_direct_nodes = self.__get_assets_ids_direct_nodes()
        assets_ids.update(_assets_ids + _assets_ids_direct_nodes)
        return assets_ids

    def _get_nodes_keys_from_db(self):
        pass

    def _get_nodes_keys_with_assets_ids_from_db(self):
        pass

    def _get_system_users_ids_from_db(self):
        pass

    def _get_resource_from_db(self, resource):
        method = '_get_{}_from_db'.format(resource)
        return getattr(self, method)()


class AssetPermissionDispatchMixin(AssetPermissionDBMixin,
                                   AssetPermissionCacheMixin):
    # dispatch
    RESOURCE = ('assets', 'nodes', 'nodes_with_assets', 'system_users')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _get_resource(self, resource):
        if resource not in self.RESOURCE:
            data = []
        elif self.cache_policy.is_using_cache:
            data = self._get_resource_from_cache(resource)
        elif self.cache_policy.is_refresh_cache:
            # TODO: 刷新资源
            data = self._get_resource_from_cache(resource)
        else:
            data = self._get_resource_from_db(resource)
        return data

    def _get_assets_ids(self):
        return self._get_resource('assets_ids')

    def _get_nodes_keys(self):
        return self._get_resource('nodes_keys')

    def _get_nodes_keys_with_assets_ids(self):
        return self._get_resource('nodes_keys_with_assets_ids')

    def _get_system_users_ids(self):
        return self._get_resource('system_users_ids')


class AssetPermissionUtil(AssetPermissionDispatchMixin):
    # interface

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_assets_ids(self):
        return self._get_assets_ids()

    def get_nodes_keys(self):
        return self._get_nodes_keys()

    def get_nodes_keys_with_assets_ids(self):
        return self._get_nodes_keys_with_assets_ids()

    def get_system_users_ids(self):
        return self._get_system_users_ids()
