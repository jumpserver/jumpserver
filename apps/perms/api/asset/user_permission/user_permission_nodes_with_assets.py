# -*- coding: utf-8 -*-
#
from itertools import chain

from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import F, Value, CharField, Q
from django.conf import settings

from orgs.utils import tmp_to_root_org
from common.permissions import IsValidUser
from common.utils import get_logger, get_object_or_none
from .mixin import UserNodeGrantStatusDispatchMixin, ForUserMixin, ForAdminMixin
from perms.utils.asset.user_permission import (
    get_indirect_granted_node_children, UNGROUPED_NODE_KEY, FAVORITE_NODE_KEY,
    get_user_direct_granted_assets, get_top_level_granted_nodes,
    get_user_granted_nodes_list_via_mapping_node,
    get_user_granted_all_assets, rebuild_user_tree_if_need,
    get_user_all_assetpermissions_id, get_favorite_node,
    get_ungrouped_node, compute_tmp_mapping_node_from_perm,
    TMP_GRANTED_FIELD, count_direct_granted_node_assets,
    count_node_all_granted_assets
)
from perms.models import AssetPermission
from assets.models import Asset, FavoriteAsset
from assets.api import SerializeToTreeNodeMixin
from perms.hands import Node

logger = get_logger(__name__)


class MyGrantedNodesWithAssetsAsTreeApi(SerializeToTreeNodeMixin, ListAPIView):
    permission_classes = (IsValidUser,)

    def add_ungrouped_resource(self, data: list, user, asset_perms_id):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return

        ungrouped_node = get_ungrouped_node(user, asset_perms_id=asset_perms_id)
        direct_granted_assets = get_user_direct_granted_assets(
            user, asset_perms_id=asset_perms_id
        ).annotate(
            parent_key=Value(ungrouped_node.key, output_field=CharField())
        ).prefetch_related('platform')

        data.extend(self.serialize_nodes([ungrouped_node], with_asset_amount=True))
        data.extend(self.serialize_assets(direct_granted_assets))

    def add_favorite_resource(self, data: list, user, asset_perms_id):
        favorite_node = get_favorite_node(user, asset_perms_id)
        favorite_assets = FavoriteAsset.get_user_favorite_assets(
            user, asset_perms_id=asset_perms_id
        ).annotate(
            parent_key=Value(favorite_node.key, output_field=CharField())
        ).prefetch_related('platform')

        data.extend(self.serialize_nodes([favorite_node], with_asset_amount=True))
        data.extend(self.serialize_assets(favorite_assets))

    def add_node_filtered_by_system_user(self, data: list, user, asset_perms_id):
        tmp_nodes = compute_tmp_mapping_node_from_perm(user, asset_perms_id=asset_perms_id)
        granted_nodes_key = []
        for _node in tmp_nodes:
            _granted = getattr(_node, TMP_GRANTED_FIELD, False)
            if not _granted:
                if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
                    assets_amount = count_direct_granted_node_assets(user, _node.key, asset_perms_id)
                else:
                    assets_amount = count_node_all_granted_assets(user, _node.key, asset_perms_id)
                _node.assets_amount = assets_amount
            else:
                granted_nodes_key.append(_node.key)

        # 查询他们的子节点
        q = Q()
        for _key in granted_nodes_key:
            q |= Q(key__startswith=f'{_key}:')

        if q:
            descendant_nodes = Node.objects.filter(q).distinct()
        else:
            descendant_nodes = Node.objects.none()

        data.extend(self.serialize_nodes(chain(tmp_nodes, descendant_nodes), with_asset_amount=True))

    def add_assets(self, data: list, user, asset_perms_id):
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            all_assets = get_user_granted_all_assets(
                user,
                via_mapping_node=False,
                include_direct_granted_assets=False,
                asset_perms_id=asset_perms_id
            )
        else:
            all_assets = get_user_granted_all_assets(
                user,
                via_mapping_node=False,
                include_direct_granted_assets=True,
                asset_perms_id=asset_perms_id
            )

        all_assets = all_assets.annotate(
            parent_key=F('nodes__key')
        ).prefetch_related('platform')
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
        asset_perms_id = get_user_all_assetpermissions_id(user)

        system_user_id = request.query_params.get('system_user')
        if system_user_id:
            asset_perms_id = list(AssetPermission.objects.valid().filter(
                id__in=asset_perms_id, system_users__id=system_user_id, actions__gt=0
            ).values_list('id', flat=True).distinct())

        self.add_ungrouped_resource(data, user, asset_perms_id)
        self.add_favorite_resource(data, user, asset_perms_id)

        if system_user_id:
            self.add_node_filtered_by_system_user(data, user, asset_perms_id)
        else:
            rebuild_user_tree_if_need(request, user)
            all_nodes = get_user_granted_nodes_list_via_mapping_node(user)
            data.extend(self.serialize_nodes(all_nodes, with_asset_amount=True))

        self.add_assets(data, user, asset_perms_id)
        return Response(data=data)


class GrantedNodeChildrenWithAssetsAsTreeApiMixin(UserNodeGrantStatusDispatchMixin,
                                                  SerializeToTreeNodeMixin,
                                                  ListAPIView):
    """
    带资产的授权树
    """
    user: None

    def get_data_on_node_direct_granted(self, key):
        nodes = Node.objects.filter(parent_key=key)
        assets = Asset.org_objects.filter(nodes__key=key).distinct()
        assets = assets.prefetch_related('platform')
        return nodes, assets

    def get_data_on_node_indirect_granted(self, key):
        user = self.user
        asset_perms_id = get_user_all_assetpermissions_id(user)

        nodes = get_indirect_granted_node_children(user, key)

        assets = Asset.org_objects.filter(
            nodes__key=key,
        ).filter(
            granted_by_permissions__id__in=asset_perms_id
        ).distinct()
        assets = assets.prefetch_related('platform')
        return nodes, assets

    def get_data_on_node_not_granted(self, key):
        return Node.objects.none(), Asset.objects.none()

    def get_data(self, key, user):
        assets, nodes = [], []
        if not key:
            root_nodes = get_top_level_granted_nodes(user)
            nodes.extend(root_nodes)
        elif key == UNGROUPED_NODE_KEY:
            assets = get_user_direct_granted_assets(user)
            assets = assets.prefetch_related('platform')
        elif key == FAVORITE_NODE_KEY:
            assets = FavoriteAsset.get_user_favorite_assets(user)
        else:
            nodes, assets = self.dispatch_get_data(key, user)
        return nodes, assets

    def id2key_if_have(self):
        id = self.request.query_params.get('id')
        if id is not None:
            node = get_object_or_none(Node, id=id)
            if node:
                return node.key

    def list(self, request: Request, *args, **kwargs):
        key = self.request.query_params.get('key')
        if key is None:
            key = self.id2key_if_have()

        user = self.user
        rebuild_user_tree_if_need(request, user)
        nodes, assets = self.get_data(key, user)

        tree_nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        tree_assets = self.serialize_assets(assets, key)
        return Response(data=[*tree_nodes, *tree_assets])


class UserGrantedNodeChildrenWithAssetsAsTreeApi(ForAdminMixin, GrantedNodeChildrenWithAssetsAsTreeApiMixin):
    pass


class MyGrantedNodeChildrenWithAssetsAsTreeApi(ForUserMixin, GrantedNodeChildrenWithAssetsAsTreeApiMixin):
    pass
