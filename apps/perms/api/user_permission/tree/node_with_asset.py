import abc

from django.conf import settings
from django.db.models import F, Value, CharField
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from assets.models import Asset
from assets.api import SerializeToTreeNodeMixin
from perms.hands import Node
from perms.models import PermNode
from perms.utils.user_permission import (
    UserGrantedNodesQueryUtils, UserGrantedAssetsQueryUtils,
)
from perms.utils.permission import AssetPermissionUtil
from common.utils import get_object_or_none, lazyproperty
from common.utils.common import timeit


from ..mixin import SelfOrPKUserMixin
from .mixin import RebuildTreeMixin

__all__ = [
    'UserPermedNodesWithAssetsAsTreeApi',
    'UserPermedNodeChildrenWithAssetsAsTreeApi'
]


class BaseUserNodeWithAssetAsTreeApi(SelfOrPKUserMixin, RebuildTreeMixin, SerializeToTreeNodeMixin,
                                     ListAPIView):

    def list(self, request, *args, **kwargs):
        nodes, assets = self.get_nodes_assets()
        tree_nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        tree_assets = self.serialize_assets(assets, node_key=self.node_key_for_serializer_assets)
        data = list(tree_nodes) + list(tree_assets)
        return Response(data=data)

    @abc.abstractmethod
    def get_nodes_assets(self):
        return [], []

    @lazyproperty
    def node_key_for_serializer_assets(self):
        return None


class UserPermedNodesWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    query_node_util: UserGrantedNodesQueryUtils
    query_asset_util: UserGrantedAssetsQueryUtils

    def get_nodes_assets(self):
        perm_ids = AssetPermissionUtil().get_permissions_for_user(self.request.user, flat=True)
        self.query_node_util = UserGrantedNodesQueryUtils(self.request.user, perm_ids)
        self.query_asset_util = UserGrantedAssetsQueryUtils(self.request.user, perm_ids)
        ung_nodes, ung_assets = self._get_nodes_assets_for_ungrouped()
        fav_nodes, fav_assets = self._get_nodes_assets_for_favorite()
        all_nodes, all_assets = self._get_nodes_assets_for_all()
        nodes = list(ung_nodes) + list(fav_nodes) + list(all_nodes)
        assets = list(ung_assets) + list(fav_assets) + list(all_assets)
        return nodes, assets

    @timeit
    def _get_nodes_assets_for_ungrouped(self):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return [], []
        node = self.query_node_util.get_ungrouped_node()
        assets = self.query_asset_util.get_ungroup_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField())) \
            .prefetch_related('platform')
        return [node], assets

    @timeit
    def _get_nodes_assets_for_favorite(self):
        node = self.query_node_util.get_favorite_node()
        assets = self.query_asset_util.get_favorite_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField())) \
            .prefetch_related('platform')
        return [node], assets

    def _get_nodes_assets_for_all(self):
        nodes = self.query_node_util.get_whole_tree_nodes(with_special=False)
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            assets = self.query_asset_util.get_direct_granted_nodes_assets()
        else:
            assets = self.query_asset_util.get_all_granted_assets()
        assets = assets.annotate(parent_key=F('nodes__key')).prefetch_related('platform')
        return nodes, assets


class UserPermedNodeChildrenWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    """ 用户授权的节点的子节点与资产树 """

    def get_nodes_assets(self):
        nodes = PermNode.objects.none()
        assets = Asset.objects.none()
        query_node_util = UserGrantedNodesQueryUtils(self.user)
        query_asset_util = UserGrantedAssetsQueryUtils(self.user)
        node_key = self.query_node_key
        if not node_key:
            nodes = query_node_util.get_top_level_nodes()
        elif node_key == PermNode.UNGROUPED_NODE_KEY:
            assets = query_asset_util.get_ungroup_assets()
        elif node_key == PermNode.FAVORITE_NODE_KEY:
            assets = query_asset_util.get_favorite_assets()
        else:
            nodes = query_node_util.get_node_children(node_key)
            assets = query_asset_util.get_node_assets(node_key)
        assets = assets.prefetch_related('platform')
        return nodes, assets

    @lazyproperty
    def query_node_key(self):
        node_key = self.request.query_params.get('key', None)
        if node_key is not None:
            return node_key
        node_id = self.request.query_params.get('id', None)
        node = get_object_or_none(Node, id=node_id)
        node_key = getattr(node, 'key', None)
        return node_key

    @lazyproperty
    def node_key_for_serializer_assets(self):
        return self.query_node_key

