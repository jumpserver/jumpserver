# -*- coding: utf-8 -*-
#
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import F, Value, CharField
from django.conf import settings

from common.utils.common import timeit
from orgs.utils import tmp_to_root_org
from common.permissions import IsValidUser
from common.utils import get_logger, get_object_or_none
from .mixin import RoleUserMixin, RoleAdminMixin
from perms.utils.asset.user_permission import (
    UserGrantedTreeBuildUtils, get_user_all_asset_perm_ids,
    UserGrantedNodesQueryUtils, UserGrantedAssetsQueryUtils,
)
from perms.models import AssetPermission, PermNode
from assets.models import Asset
from assets.api import SerializeToTreeNodeMixin
from perms.hands import Node

logger = get_logger(__name__)


class MyGrantedNodesWithAssetsAsTreeApi(SerializeToTreeNodeMixin, ListAPIView):
    permission_classes = (IsValidUser,)

    @timeit
    def add_ungrouped_resource(self, data: list, nodes_query_utils, assets_query_utils):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return
        ungrouped_node = nodes_query_utils.get_ungrouped_node()

        direct_granted_assets = assets_query_utils.get_direct_granted_assets().annotate(
            parent_key=Value(ungrouped_node.key, output_field=CharField())
        ).prefetch_related('platform')

        data.extend(self.serialize_nodes([ungrouped_node], with_asset_amount=True))
        data.extend(self.serialize_assets(direct_granted_assets))

    @timeit
    def add_favorite_resource(self, data: list, nodes_query_utils, assets_query_utils):
        favorite_node = nodes_query_utils.get_favorite_node()

        favorite_assets = assets_query_utils.get_favorite_assets()
        favorite_assets = favorite_assets.annotate(
            parent_key=Value(favorite_node.key, output_field=CharField())
        ).prefetch_related('platform')

        data.extend(self.serialize_nodes([favorite_node], with_asset_amount=True))
        data.extend(self.serialize_assets(favorite_assets))

    @timeit
    def add_node_filtered_by_system_user(self, data: list, user, asset_perms_id):
        utils = UserGrantedTreeBuildUtils(user, asset_perms_id)
        nodes = utils.get_whole_tree_nodes()
        data.extend(self.serialize_nodes(nodes, with_asset_amount=True))

    def add_assets(self, data: list, assets_query_utils: UserGrantedAssetsQueryUtils):
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            all_assets = assets_query_utils.get_direct_granted_nodes_assets()
        else:
            all_assets = assets_query_utils.get_all_granted_assets()
        all_assets = all_assets.annotate(parent_key=F('nodes__key')).prefetch_related('platform')
        data.extend(self.serialize_assets(all_assets))

    @tmp_to_root_org()
    def list(self, request: Request, *args, **kwargs):
        """
        此算法依赖 UserGrantedMappingNode
        获取所有授权的节点和资产

        Node = UserGrantedMappingNode + 授权节点的子节点
        Asset = 授权节点的资产 + 直接授权的资产
        """

        user = request.user
        data = []
        asset_perms_id = get_user_all_asset_perm_ids(user)

        system_user_id = request.query_params.get('system_user')
        if system_user_id:
            asset_perms_id = list(AssetPermission.objects.valid().filter(
                id__in=asset_perms_id, system_users__id=system_user_id, actions__gt=0
            ).values_list('id', flat=True).distinct())

        nodes_query_utils = UserGrantedNodesQueryUtils(user, asset_perms_id)
        assets_query_utils = UserGrantedAssetsQueryUtils(user, asset_perms_id)

        self.add_ungrouped_resource(data, nodes_query_utils, assets_query_utils)
        self.add_favorite_resource(data, nodes_query_utils, assets_query_utils)

        if system_user_id:
            # 有系统用户筛选的需要重新计算树结构
            self.add_node_filtered_by_system_user(data, user, asset_perms_id)
        else:
            all_nodes = nodes_query_utils.get_whole_tree_nodes(with_special=False)
            data.extend(self.serialize_nodes(all_nodes, with_asset_amount=True))

        self.add_assets(data, assets_query_utils)
        return Response(data=data)


class GrantedNodeChildrenWithAssetsAsTreeApiMixin(SerializeToTreeNodeMixin,
                                                  ListAPIView):
    """
    带资产的授权树
    """
    user: None

    def ensure_key(self):
        key = self.request.query_params.get('key', None)
        id = self.request.query_params.get('id', None)

        if key is not None:
            return key

        node = get_object_or_none(Node, id=id)
        if node:
            return node.key

    def list(self, request: Request, *args, **kwargs):
        user = self.user
        key = self.ensure_key()

        nodes_query_utils = UserGrantedNodesQueryUtils(user)
        assets_query_utils = UserGrantedAssetsQueryUtils(user)

        nodes = PermNode.objects.none()
        assets = Asset.objects.none()

        if not key:
            nodes = nodes_query_utils.get_top_level_nodes()
        elif key == PermNode.UNGROUPED_NODE_KEY:
            assets = assets_query_utils.get_ungroup_assets()
        elif key == PermNode.FAVORITE_NODE_KEY:
            assets = assets_query_utils.get_favorite_assets()
        else:
            nodes = nodes_query_utils.get_node_children(key)
            assets = assets_query_utils.get_node_assets(key)
        assets = assets.prefetch_related('platform')

        tree_nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        tree_assets = self.serialize_assets(assets, key)
        return Response(data=[*tree_nodes, *tree_assets])


class UserGrantedNodeChildrenWithAssetsAsTreeApi(RoleAdminMixin, GrantedNodeChildrenWithAssetsAsTreeApiMixin):
    pass


class MyGrantedNodeChildrenWithAssetsAsTreeApi(RoleUserMixin, GrantedNodeChildrenWithAssetsAsTreeApiMixin):
    pass
