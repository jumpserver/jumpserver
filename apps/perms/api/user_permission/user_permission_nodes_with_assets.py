# -*- coding: utf-8 -*-
#
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from django.db.models import Q, F

from common.permissions import IsValidUser
from common.utils.django import get_object_or_none
from common.utils import get_logger
from .mixin import UserGrantedNodeDispatchMixin, ForUserMixin, ForAdminMixin
from perms.models import UserGrantedMappingNode
from perms.utils.user_node_tree import (
    node_annotate_mapping_node, get_ungrouped_node,
    is_granted, get_granted_assets_amount, node_annotate_set_granted,
    get_granted_query, get_ungranted_node_children, UNGROUPED_NODE_KEY,
    get_direct_granted_assets
)

from assets.models import Asset
from assets.api import SerializeToTreeNodeMixin
from orgs.utils import tmp_to_root_org
from ...hands import Node

logger = get_logger(__name__)


class MyGrantedNodesWithAssetsAsTreeApi(SerializeToTreeNodeMixin, ListAPIView):
    permission_classes = (IsValidUser,)

    @tmp_to_root_org()
    def list(self, request: Request, *args, **kwargs):
        """
        Node = UserGrantedMappingNode + 授权节点的子节点
        Asset = 授权节点的资产 + 直接授权的资产
        """

        user = request.user

        # 获取 `UserGrantedMappingNode` 中对应的 `Node`
        nodes = Node.objects.filter(
            mapping_nodes__user=user,
        ).annotate(**node_annotate_mapping_node).distinct()

        key2nodes_mapper = {}
        descendant_q = Q()
        granted_q = Q()

        for _node in nodes:
            if not is_granted(_node):
                # 未授权的节点资产数量设置为 `UserGrantedMappingNode` 中的数量
                _node.assets_amount = get_granted_assets_amount(_node)
            else:
                # 直接授权的节点

                # 增加查询该节点及其后代节点资产的过滤条件
                granted_q |= Q(nodes__key__startswith=f'{_node.key}:')
                granted_q |= Q(nodes__key=_node.key)

                # 增加查询后代节点的过滤条件
                descendant_q |= Q(key__startswith=f'{_node.key}:')

            key2nodes_mapper[_node.key] = _node

        if descendant_q:
            descendant_nodes = Node.objects.filter(descendant_q).annotate(**node_annotate_set_granted)
            for _node in descendant_nodes:
                key2nodes_mapper[_node.key] = _node

        all_nodes = key2nodes_mapper.values()

        # 查询出所有资产
        all_assets = Asset.objects.filter(
            get_granted_query(user) |
            granted_q
        ).annotate(parent_key=F('nodes__key')).distinct()

        data = [
            *self.serialize_nodes(all_nodes, with_asset_amount=True),
            *self.serialize_assets(all_assets)
        ]
        return Response(data=data)


class UserGrantedNodeChildrenWithAssetsAsTreeForAdminApi(ForAdminMixin, UserGrantedNodeDispatchMixin, SerializeToTreeNodeMixin, ListAPIView):
    """
    带资产的授权树
    """

    def on_direct_granted_node(self, key, mapping_node: UserGrantedMappingNode, node: Node = None):
        nodes = Node.objects.filter(parent_key=key)
        assets = Asset.org_objects.filter(nodes__key=key).distinct()
        assets = assets.prefetch_related('platform')
        return nodes, assets

    def on_undirect_granted_node(self, key, mapping_node: UserGrantedMappingNode, node: Node = None):
        user = self.user
        assets = Asset.objects.none()

        nodes = get_ungranted_node_children(user, key)

        if mapping_node.asset_granted:
            assets = Asset.org_objects.filter(
                nodes__key=key,
            ).filter(get_granted_query(user)).distinct()
            assets = assets.prefetch_related('platform')
        return nodes, assets

    @tmp_to_root_org()
    def list(self, request: Request, *args, **kwargs):
        user = self.user
        key = request.query_params.get('key')
        self.submit_update_mapping_node_task(user)

        nodes = []
        assets = []
        if not key:
            root_nodes = get_ungranted_node_children(user)
            ungrouped_node = get_ungrouped_node(user)
            nodes.append(ungrouped_node)
            nodes.extend(root_nodes)
        elif key == UNGROUPED_NODE_KEY:
            assets = get_direct_granted_assets(user)
            assets = assets.prefetch_related('platform')
        else:
            mapping_node: UserGrantedMappingNode = get_object_or_none(
                UserGrantedMappingNode, user=user, key=key)
            nodes, assets = self.dispatch_node_process(key, mapping_node)
        nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        assets = self.serialize_assets(assets, key)
        return Response(data=[*nodes, *assets])


class MyGrantedNodeChildrenWithAssetsAsTreeApi(ForUserMixin, UserGrantedNodeChildrenWithAssetsAsTreeForAdminApi):
    pass
