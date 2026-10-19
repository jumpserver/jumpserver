import json
import re

from django.conf import settings
from django.core.cache import cache
from django.db.models import CharField, Q
from django.db.models.functions import Cast
from django.utils.translation import get_language
from rest_framework.utils.encoders import JSONEncoder

from assets.const import AllTypes
from assets.models import FavoriteAsset, Asset, Node
from common.utils import lazyproperty
from common.utils.common import timeit, get_logger
from orgs.utils import current_org, get_current_org, get_current_org_id
from perms.models import PermNode, AssetPermission

__all__ = ['AssetPermissionPermAssetUtil', 'UserPermAssetUtil', 'UserPermNodeUtil']

logger = get_logger(__name__)
USER_PERMISSION_IDS_CACHE_TIMEOUT = 15
# A large OR of materialized-path prefixes becomes disproportionately expensive
# to plan and execute. Above this size, scan the current org's much smaller node
# key set once and keep the matching node ids.
SUBTREE_QUERY_KEY_LIMIT = 100


class AssetPermissionPermAssetUtil:

    def __init__(self, perm_ids):
        # Evaluate this small set once. Reusing a lazy permission queryset in
        # every node and asset subquery otherwise repeats the user/group joins.
        self.perm_ids = set(perm_ids)

    def get_all_assets(self):
        if self.is_current_org_root_fully_granted():
            return Asset.objects.all().order_by()
        node_assets = self.get_perm_nodes_assets()
        direct_assets = self.get_direct_assets()
        # 比原来的查到所有 asset id 再搜索块很多，因为当资产量大的时候，搜索会很慢
        return (node_assets | direct_assets).order_by().distinct()

    def get_perm_nodes(self):
        """ 获取所有授权节点 """
        node_ids = AssetPermission.nodes.through.objects.filter(
            assetpermission_id__in=self.perm_ids
        ).values('node_id').distinct()
        nodes = Node.objects.filter(id__in=node_ids).only('id', 'key')
        return nodes

    def get_direct_node_keys(self):
        nodes = self.get_perm_nodes()
        root_nodes = list(
            nodes.filter(parent_key='').values_list('key', 'org_id')
        )
        org = get_current_org()
        if root_nodes and org and not org.is_root():
            return tuple(node[0] for node in root_nodes)

        root_org_ids = {node[1] for node in root_nodes}
        if root_org_ids:
            nodes = nodes.exclude(org_id__in=root_org_ids)
        keys = {node[0] for node in root_nodes}
        keys.update(nodes.values_list('key', flat=True))
        return tuple(Node.clean_children_keys(keys))

    @lazyproperty
    def direct_node_keys(self):
        return self.get_direct_node_keys()

    @lazyproperty
    def direct_node_key_set(self):
        return set(self.direct_node_keys)

    @staticmethod
    def is_key_in_subtrees(key, subtree_keys):
        current = key
        while current:
            if current in subtree_keys:
                return True
            current = current.rpartition(':')[0]
        return False

    def is_current_org_root_fully_granted(self):
        org = get_current_org()
        if not org or org.is_root():
            return False
        return any(':' not in key for key in self.direct_node_keys)

    def get_descendant_nodes(self, keys=None):
        if keys is None:
            keys = self.direct_node_keys
        keys = Node.clean_children_keys(keys)
        if len(keys) > SUBTREE_QUERY_KEY_LIMIT:
            key_set = set(keys)
            node_ids = (
                node_id
                for node_id, key in
                Node.objects.order_by().values_list('id', 'key').iterator(
                    chunk_size=10000
                )
                if self.is_key_in_subtrees(key, key_set)
            )
            return Node.objects.filter(id__in=list(node_ids)).order_by()

        query = Q()
        for key in keys:
            query |= Q(key=key) | Q(key__startswith=f'{key}:')
        if not query:
            return Node.objects.none()
        return Node.objects.filter(query).order_by()

    @timeit
    def get_perm_nodes_assets(self):
        """ 获取所有授权节点下的资产 """
        node_ids = self.get_descendant_nodes().values('id')
        return Asset.objects.filter(nodes__id__in=node_ids).order_by()

    @lazyproperty
    def direct_asset_ids(self):
        return AssetPermission.assets.through.objects \
            .filter(assetpermission_id__in=self.perm_ids) \
            .values('asset_id') \
            .distinct()

    @timeit
    def get_direct_assets(self):
        """ 获取直接授权的资产 """
        return Asset.objects.filter(id__in=self.direct_asset_ids).order_by()

    def get_direct_assets_count(self):
        """Count direct grants without joining the full asset table."""
        return self.direct_asset_ids.count()


class UserPermAssetUtil(AssetPermissionPermAssetUtil):

    def __init__(self, user, perm_ids=None):
        self.user = user
        if perm_ids is None:
            perm_ids = self.get_permission_ids()
        super().__init__(perm_ids)

    def get_permission_ids(self):
        cache_key = (
            f'perms:user-permission-ids:{self.user.id}:'
            f'{get_current_org_id()}'
        )
        perm_ids = cache.get(cache_key)
        if perm_ids is not None:
            return perm_ids

        joined_org_ids = tuple(
            str(org_id) for org_id in
            self.user.orgs.values_list('id', flat=True)
        )
        if not joined_org_ids:
            cache.set(
                cache_key, (), timeout=USER_PERMISSION_IDS_CACHE_TIMEOUT
            )
            return ()

        direct_perm_ids = set(
            AssetPermission.users.through.objects
            .filter(user_id=self.user.id)
            .annotate(
                permission_key=Cast('assetpermission_id', CharField())
            )
            .values_list('permission_key', flat=True)
        )
        user_group_ids = (
            self.user.groups.through.objects
            .filter(user_id=self.user.id)
            .values_list('usergroup_id', flat=True)
        )
        group_perm_ids = set(
            AssetPermission.user_groups.through.objects
            .filter(usergroup_id__in=user_group_ids)
            .annotate(
                permission_key=Cast('assetpermission_id', CharField())
            )
            .values_list('permission_key', flat=True)
        )
        related_perm_ids = direct_perm_ids | group_perm_ids
        if related_perm_ids:
            perm_ids = tuple(
                AssetPermission.objects.valid()
                .filter(
                    id__in=related_perm_ids,
                    org_id__in=joined_org_ids,
                )
                .annotate(permission_key=Cast('id', CharField()))
                .order_by()
                .values_list('permission_key', flat=True)
            )
        else:
            perm_ids = ()

        cache.set(
            cache_key,
            perm_ids,
            timeout=USER_PERMISSION_IDS_CACHE_TIMEOUT,
        )
        return perm_ids

    def get_direct_node_keys(self):
        cache_key = (
            f'perms:user-permission-node-keys:{self.user.id}:'
            f'{get_current_org_id()}'
        )
        keys = cache.get(cache_key)
        if keys is None:
            keys = super().get_direct_node_keys()
            cache.set(
                cache_key,
                keys,
                timeout=USER_PERMISSION_IDS_CACHE_TIMEOUT,
            )
        return keys

    def get_ungroup_assets(self):
        return self.get_direct_assets()

    @timeit
    def get_favorite_assets(self):
        assets = Asset.objects.all().valid()
        asset_ids = FavoriteAsset.objects.filter(user=self.user).values_list('asset_id', flat=True)
        assets = assets.filter(id__in=list(asset_ids))
        return assets

    def get_type_nodes_tree(self):
        assets = self.get_all_assets()
        resource_platforms = assets.order_by('id').values_list('platform_id', flat=True)
        node_all = AllTypes.get_tree_nodes(resource_platforms, get_root=True)
        pattern = re.compile(r'\(0\)?')
        nodes = []
        for node in node_all:
            meta = node.get('meta', {})
            if pattern.search(node['name']) or meta.get('type') == 'platform':
                continue
            _type = meta.get('_type')
            if _type:
                node['type'] = _type
                node['category'] = meta.get('category')
            meta.setdefault('data', {})
            node['meta'] = meta
            nodes.append(node)
        return nodes

    @classmethod
    def get_type_nodes_tree_or_cached(cls, user):
        lang = get_language()
        key = f'perms:type-nodes-tree:{user.id}:{current_org.id}:{lang}'
        nodes = cache.get(key)
        if nodes is None:
            nodes = cls(user).get_type_nodes_tree()
            nodes_json = json.dumps(nodes, cls=JSONEncoder)
            cache.set(key, nodes_json, 60)
        else:
            nodes = json.loads(nodes)
        return nodes

    @classmethod
    def refresh_type_nodes_tree_cache(cls, user_ids=None, org_id=None):
        if user_ids is None:
            user_ids = []

        if org_id is None:
            org_id = get_current_org_id()

        logger.debug("Refresh type nodes tree cache")
        for user_id in user_ids:
            key = f'perms:type-nodes-tree:{user_id}:{org_id}*'
            cache.delete_pattern(key)

    def refresh_favorite_assets(self):
        favor_ids = FavoriteAsset.objects.filter(user=self.user).values_list('asset_id', flat=True)
        favor_ids = set(favor_ids)

        valid_ids = self.get_all_assets() \
            .filter(id__in=favor_ids) \
            .values_list('id', flat=True)
        valid_ids = set(valid_ids)

        invalid_ids = favor_ids - valid_ids
        FavoriteAsset.objects.filter(user=self.user, asset_id__in=invalid_ids).delete()

    def get_node_assets(self, key):
        if self.is_node_fully_granted(key):
            assets = Asset.objects.filter(nodes__key=key).order_by()
        elif not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            assets = self.get_direct_assets().filter(nodes__key=key)
        else:
            assets = Asset.objects.none()
        return assets.order_by().distinct()

    def get_node_all_assets(self, node_id):
        """ 获取节点下的所有资产 """
        node = PermNode.objects.get(id=node_id)
        node_subtree_filter = (
            Q(nodes__key=node.key) |
            Q(nodes__key__startswith=f'{node.key}:')
        )
        if self.is_node_fully_granted(node.key):
            assets = Asset.objects.filter(node_subtree_filter)
            return node, assets.order_by().distinct()

        granted_keys = [
            granted_key for granted_key in self.direct_node_keys
            if granted_key.startswith(f'{node.key}:')
        ]
        granted_node_ids = self.get_descendant_nodes(granted_keys).values('id')
        node_assets = Asset.objects.filter(nodes__id__in=granted_node_ids)
        direct_assets = Asset.objects.none()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            direct_assets = self.get_direct_assets().filter(
                node_subtree_filter
            )
        assets = (node_assets | direct_assets).order_by().distinct()
        return node, assets

    def is_node_fully_granted(self, key):
        return self.is_key_in_subtrees(
            key, self.direct_node_key_set
        )


class UserPermNodeUtil:

    node_only_fields = (
        'id', 'key', 'parent_key', 'org_id', 'value',
        'full_value', 'assets_amount',
    )

    def __init__(self, user, asset_util=None):
        self.user = user
        self.asset_util = asset_util or UserPermAssetUtil(user)
        self.perm_ids = self.asset_util.perm_ids

    def get_favorite_node(self, with_asset_count=True):
        assets_amount = 0
        if with_asset_count:
            favor_ids = FavoriteAsset.objects \
                .filter(user=self.user) \
                .values_list('asset_id') \
                .distinct()
            assets_amount = Asset.objects.all().valid().filter(
                id__in=favor_ids
            ).count()
        return PermNode.get_favorite_node(assets_amount)

    def get_ungrouped_node(self, with_asset_count=True):
        assets_amount = (
            self.asset_util.get_direct_assets_count()
            if with_asset_count else 0
        )
        return PermNode.get_ungrouped_node(assets_amount)

    def get_top_level_nodes(self, with_unfolded_node=False):
        # 是否有节点展开, 展开的节点
        unfolded_node = None
        nodes = self.get_special_nodes()
        real_nodes = list(self._get_visible_node_children(key=''))
        nodes.extend(real_nodes)
        if len(real_nodes) == 1:
            unfolded_node = real_nodes[0]
            children = self.get_node_children(unfolded_node.key)
            nodes.extend(children)
        if with_unfolded_node:
            return nodes, unfolded_node
        else:
            return nodes

    def get_special_nodes(
            self, with_asset_count=True, include_favorites=True
    ):
        nodes = []
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            ung_node = self.get_ungrouped_node(with_asset_count)
            nodes.append(ung_node)
        if include_favorites:
            nodes.append(self.get_favorite_node(with_asset_count))
        return nodes

    def get_root_nodes(
            self, with_asset_count=True, include_favorites=True
    ):
        nodes = self.get_special_nodes(
            with_asset_count=with_asset_count,
            include_favorites=include_favorites,
        )
        nodes.extend(self._get_visible_node_children(''))
        return nodes

    def get_node_children(self, key):
        if not key:
            return self.get_root_nodes()

        if key in [PermNode.FAVORITE_NODE_KEY, PermNode.UNGROUPED_NODE_KEY]:
            return PermNode.objects.none()

        if self.asset_util.is_node_fully_granted(key):
            return PermNode.objects.filter(parent_key=key).only(
                *self.node_only_fields
            ).order_by('value', 'id')
        return self._get_visible_node_children(key)

    @lazyproperty
    def direct_asset_node_keys(self):
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return ()
        if self.asset_util.is_current_org_root_fully_granted():
            return ()
        cache_key = (
            f'perms:user-direct-asset-node-keys:{self.user.id}:'
            f'{get_current_org_id()}'
        )
        cached_keys = cache.get(cache_key)
        if cached_keys is not None:
            return cached_keys
        keys = Asset.nodes.through.objects.filter(
            asset_id__in=self.asset_util.direct_asset_ids
        ).values_list('node__key', flat=True).distinct()
        keys = tuple(
            key for key in keys
            if not self.asset_util.is_node_fully_granted(key)
        )
        cache.set(
            cache_key,
            keys,
            timeout=USER_PERMISSION_IDS_CACHE_TIMEOUT,
        )
        return keys

    @lazyproperty
    def visible_ancestor_keys(self):
        keys = set()
        anchors = (*self.asset_util.direct_node_keys, *self.direct_asset_node_keys)
        for key in anchors:
            keys.update(Node.get_node_ancestor_keys(key, with_self=True))
        return keys

    def _get_visible_node_children(self, key):
        if not self.visible_ancestor_keys:
            return PermNode.objects.none()
        return PermNode.objects.filter(
            parent_key=key, key__in=self.visible_ancestor_keys
        ).only(*self.node_only_fields).order_by('value', 'id')

    @timeit
    def get_whole_tree_nodes(self, with_special=True):
        query = Q(key__in=self.visible_ancestor_keys)
        for key in self.asset_util.direct_node_keys:
            query |= Q(key__startswith=f'{key}:')
        real_nodes = list(
            PermNode.objects.filter(query).only(*self.node_only_fields)
            if query else PermNode.objects.none()
        )
        nodes = []
        if with_special:
            nodes.extend(self.get_special_nodes())
        nodes.extend(real_nodes)
        return nodes
