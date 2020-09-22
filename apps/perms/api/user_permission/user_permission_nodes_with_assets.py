# -*- coding: utf-8 -*-
#
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import Q, F

from common.permissions import IsValidUser
from common.utils import get_logger
from .mixin import UserNodeGrantStatusDispatchMixin, ForUserMixin, ForAdminMixin
from perms.utils.user_node_tree import (
    node_annotate_mapping_node,
    is_direct_granted_by_annotate, get_granted_assets_amount, node_annotate_set_granted,
    get_user_direct_granted_resources_q_by_asset_permissions,
    get_indirect_granted_node_children, UNGROUPED_NODE_KEY,
    get_direct_granted_assets, get_top_level_granted_nodes
)

from assets.models import Asset
from assets.api import SerializeToTreeNodeMixin
from orgs.utils import tmp_to_root_org
from ...hands import Node

logger = get_logger(__name__)


class MyGrantedNodesWithAssetsAsTreeApi(SerializeToTreeNodeMixin, ListAPIView):
    permission_classes = (IsValidUser,)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assets_granted_by_nodes_q = Q()

    def get_all_granted_nodes(self, user):
        # 获取 `UserGrantedMappingNode` 中对应的 `Node`
        nodes = Node.objects.filter(
            mapping_nodes__user=user,
        ).annotate(
            **node_annotate_mapping_node
        ).distinct()

        key_to_node_mapper = {}
        nodes_descendant_q = Q()

        for _node in nodes:
            if not is_direct_granted_by_annotate(_node):
                # 未授权的节点资产数量设置为 `UserGrantedMappingNode` 中的数量
                _node.assets_amount = get_granted_assets_amount(_node)
            else:
                # 直接授权的节点

                # 增加查询后代节点的过滤条件
                nodes_descendant_q |= Q(key__startswith=f'{_node.key}:')

                # 增加查询该节点及其后代节点资产的过滤条件
                self.assets_granted_by_nodes_q |= Q(nodes__key__startswith=f'{_node.key}:')
                self.assets_granted_by_nodes_q |= Q(nodes__key=_node.key)

            key_to_node_mapper[_node.key] = _node

        if nodes_descendant_q:
            descendant_nodes = Node.objects.filter(
                nodes_descendant_q
            ).annotate(
                **node_annotate_set_granted
            )
            for _node in descendant_nodes:
                key_to_node_mapper[_node.key] = _node

        return list(key_to_node_mapper.values())

    def get_all_granted_assets(self, user):
        # 查询出所有资产

        direct_q = get_user_direct_granted_resources_q_by_asset_permissions(user)
        q = direct_q | self.assets_granted_by_nodes_q

        all_assets = Asset.objects.filter(q)\
            .annotate(parent_key=F('nodes__key'))\
            .distinct()
        return all_assets

    @tmp_to_root_org()
    def list(self, request: Request, *args, **kwargs):
        """
        此算法依赖 UserGrantedMappingNode
        获取所有授权的节点和资产

        Node = UserGrantedMappingNode + 授权节点的子节点
        Asset = 授权节点的资产 + 直接授权的资产
        """

        user = request.user
        all_nodes = self.get_all_granted_nodes(user)
        all_assets = self.get_all_granted_assets(user)

        data = [
            *self.serialize_nodes(all_nodes, with_asset_amount=True),
            *self.serialize_assets(all_assets)
        ]
        return Response(data=data)


class UserGrantedNodeChildrenWithAssetsAsTreeForAdminApi(ForAdminMixin, UserNodeGrantStatusDispatchMixin,
                                                         SerializeToTreeNodeMixin, ListAPIView):
    """
    带资产的授权树
    """

    def get_data_on_node_direct_granted(self, key):
        nodes = Node.objects.filter(parent_key=key)
        assets = Asset.org_objects.filter(nodes__key=key).distinct()
        assets = assets.prefetch_related('platform')
        return nodes, assets

    def get_data_on_node_indirect_granted(self, key):
        user = self.user
        nodes = get_indirect_granted_node_children(user, key)
        direct_granted_q = get_user_direct_granted_resources_q_by_asset_permissions(user)

        assets = Asset.org_objects.filter(
            nodes__key=key,
        ).filter(
            direct_granted_q
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
            assets = get_direct_granted_assets(user)
            assets = assets.prefetch_related('platform')
        else:
            nodes, assets = self.dispatch_get_data(key, user)
        return nodes, assets

    @tmp_to_root_org()
    def list(self, request: Request, *args, **kwargs):
        self.submit_update_mapping_node_task(self.user)
        key = self.request.query_params.get('key')
        user = self.user
        nodes, assets = self.get_data(key, user)

        tree_nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        tree_assets = self.serialize_assets(assets, key)
        return Response(data=[*tree_nodes, *tree_assets])


class MyGrantedNodeChildrenWithAssetsAsTreeApi(ForUserMixin, UserGrantedNodeChildrenWithAssetsAsTreeForAdminApi):
    pass
