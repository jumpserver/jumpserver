import abc

from django.conf import settings
from django.db.models import F, Value, CharField
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from assets.api import SerializeToTreeNodeMixin
from assets.models import Asset
from common.utils import get_object_or_none, lazyproperty
from common.utils.common import timeit
from perms.hands import Node
from perms.models import PermNode
from perms.utils import UserPermAssetUtil
from perms.utils import UserPermNodeUtil
from .mixin import RebuildTreeMixin
from ..mixin import SelfOrPKUserMixin

__all__ = [
    'UserPermedNodesWithAssetsAsTreeApi',
    'UserPermedNodeChildrenWithAssetsAsTreeApi',
    'UserPermedNodeChildrenWithAssetsAsCategoryTreeApi',
]


class BaseUserNodeWithAssetAsTreeApi(
    SelfOrPKUserMixin, RebuildTreeMixin,
    SerializeToTreeNodeMixin, ListAPIView
):
    page_limit = 10000

    def list(self, request, *args, **kwargs):
        offset = int(request.query_params.get('offset', 0))
        page_assets = self.get_page_assets()

        if not offset:
            nodes, assets = self.get_nodes_assets()
            page = page_assets[:self.page_limit]
            assets = [*assets, *page]
            tree_nodes = self.serialize_nodes(nodes, with_asset_amount=True)
            tree_assets = self.serialize_assets(assets, **self.serialize_asset_kwargs)
            data = list(tree_nodes) + list(tree_assets)
        else:
            page = page_assets[offset:(offset + self.page_limit)]
            data = self.serialize_assets(page, **self.serialize_asset_kwargs) if page else []
        offset += len(page)
        headers = {'X-JMS-TREE-OFFSET': offset} if offset else {}
        return Response(data=data, headers=headers)

    @abc.abstractmethod
    def get_nodes_assets(self):
        return [], []

    def get_page_assets(self):
        return []

    @property
    def serialize_asset_kwargs(self):
        return {}


class UserPermedNodesWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    query_node_util: UserPermNodeUtil
    query_asset_util: UserPermAssetUtil

    def get_nodes_assets(self):
        self.query_node_util = UserPermNodeUtil(self.request.user)
        ung_nodes, ung_assets = self._get_nodes_assets_for_ungrouped()
        fav_nodes, fav_assets = self._get_nodes_assets_for_favorite()
        all_nodes, all_assets = self._get_nodes_assets_for_all()
        nodes = list(ung_nodes) + list(fav_nodes) + list(all_nodes)
        assets = list(ung_assets) + list(fav_assets) + list(all_assets)
        return nodes, assets

    def get_page_assets(self):
        return self.query_asset_util.get_all_assets().annotate(parent_key=F('nodes__key'))

    @timeit
    def _get_nodes_assets_for_ungrouped(self):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return [], []
        node = self.query_node_util.get_ungrouped_node()
        assets = self.query_asset_util.get_ungroup_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField()))
        return [node], assets

    @lazyproperty
    def query_asset_util(self):
        return UserPermAssetUtil(self.user)

    @timeit
    def _get_nodes_assets_for_favorite(self):
        node = self.query_node_util.get_favorite_node()
        assets = self.query_asset_util.get_favorite_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField()))
        return [node], assets

    @timeit
    def _get_nodes_assets_for_all(self):
        nodes = self.query_node_util.get_whole_tree_nodes(with_special=False)
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            assets = self.query_asset_util.get_perm_nodes_assets()
        else:
            assets = Asset.objects.none()
        assets = assets.annotate(parent_key=F('nodes__key'))
        return nodes, assets


class UserPermedNodeChildrenWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    """ 用户授权的节点的子节点与资产树 """

    # 默认展开的节点key
    default_unfolded_node_key = None

    @timeit
    def get_nodes_assets(self):
        query_node_util = UserPermNodeUtil(self.user)
        query_asset_util = UserPermAssetUtil(self.user)
        node_key = self.query_node_key
        if not node_key:
            nodes, unfolded_node = query_node_util.get_top_level_nodes(with_unfolded_node=True)
            if unfolded_node:
                """ 默认展开的节点, 获取根节点下的资产 """
                assets = query_asset_util.get_node_assets(key=unfolded_node.key)
                self.default_unfolded_node_key = unfolded_node.key
            else:
                assets = Asset.objects.none()
        elif node_key == PermNode.UNGROUPED_NODE_KEY:
            nodes = PermNode.objects.none()
            assets = query_asset_util.get_ungroup_assets()
        elif node_key == PermNode.FAVORITE_NODE_KEY:
            nodes = PermNode.objects.none()
            assets = query_asset_util.get_favorite_assets()
        else:
            nodes = query_node_util.get_node_children(node_key)
            assets = query_asset_util.get_node_assets(key=node_key)
        assets = assets.prefetch_related('platform')
        return nodes, assets

    @lazyproperty
    def query_node_key(self):
        node_key = self.request.query_params.get('key', None)
        if node_key is None:
            node_id = self.request.query_params.get('id', None)
            node = get_object_or_none(Node, id=node_id)
            node_key = getattr(node, 'key', None)
        return node_key

    @property
    def serialize_asset_kwargs(self):
        return {
            'node_key': self.query_node_key or self.default_unfolded_node_key
        }


class UserPermedNodeChildrenWithAssetsAsCategoryTreeApi(BaseUserNodeWithAssetAsTreeApi):
    @property
    def is_sync(self):
        sync = self.request.query_params.get('sync', 0)
        return int(sync) == 1

    @property
    def tp(self):
        params = self.request.query_params
        return [params.get('category'), params.get('type')]

    @lazyproperty
    def query_asset_util(self):
        return UserPermAssetUtil(self.user)

    @timeit
    def get_assets(self):
        return self.query_asset_util.get_all_assets()

    def _get_tree_nodes_async(self):
        if self.request.query_params.get('lv') == '0':
            return [], []
        if not self.tp or not all(self.tp):
            nodes = UserPermAssetUtil.get_type_nodes_tree_or_cached(self.user)
            return nodes, []

        category, tp = self.tp
        assets = self.get_assets().filter(platform__type=tp, platform__category=category)
        return [], assets

    def _get_tree_nodes_sync(self):
        if self.request.query_params.get('lv'):
            return []
        nodes = self.query_asset_util.get_type_nodes_tree()
        return nodes, []

    @property
    def serialize_asset_kwargs(self):
        return {
            'get_pid': lambda asset, platform: 'ROOT_{}_{}'.format(platform.category.upper(), platform.type),
        }

    def serialize_nodes(self, nodes, with_asset_amount=False):
        return nodes

    def get_nodes_assets(self):
        if self.is_sync:
            return self._get_tree_nodes_sync()
        else:
            return self._get_tree_nodes_async()

    def get_page_assets(self):
        if self.is_sync:
            return self.get_assets()
        else:
            return []
