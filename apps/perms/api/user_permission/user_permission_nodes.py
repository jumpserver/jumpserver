# -*- coding: utf-8 -*-
#
from django.db.models import Q, F
from perms.api.user_permission.mixin import ForAdminMixin, ForUserMixin
from rest_framework.generics import (
    ListAPIView
)
from rest_framework.response import Response

from perms.utils.user_node_tree import (
    node_annotate_mapping_node, get_ungranted_node_children,
    is_granted, get_granted_assets_amount, node_annotate_set_granted,
    get_ungrouped_node,
)
from common.utils.django import get_object_or_none
from common.utils import lazyproperty
from perms.models import UserGrantedMappingNode
from orgs.utils import tmp_to_root_org
from assets.api.mixin import SerializeToTreeNodeMixin
from common.utils import get_logger
from ...hands import Node
from .mixin import UserGrantedNodeDispatchMixin
from ... import serializers


logger = get_logger(__name__)

__all__ = [
    'UserGrantedNodesForAdminApi',
    'MyGrantedNodesApi',
    'MyGrantedNodesAsTreeApi',
    'UserGrantedNodeChildrenForAdminApi',
    'MyGrantedNodeChildrenApi',
    'UserGrantedNodeChildrenAsTreeForAdminApi',
    'MyGrantedNodeChildrenAsTreeApi',
    'NodeChildrenAsTreeApi',
]


class GrantedNodeBaseApi(ListAPIView):
    @lazyproperty
    def user(self):
        raise NotImplementedError

    def get_nodes(self):
        # 不使用 `get_queryset` 单独定义 `get_nodes` 的原因是
        # `get_nodes` 返回的不一定是 `queryset`
        raise NotImplementedError


class NodeChildrenApi(GrantedNodeBaseApi):
    serializer_class = serializers.NodeGrantedSerializer

    @tmp_to_root_org()
    def list(self, request, *args, **kwargs):
        nodes = self.get_nodes()
        serializer = self.get_serializer(nodes, many=True)
        return Response(serializer.data)


class NodeChildrenAsTreeApi(SerializeToTreeNodeMixin, GrantedNodeBaseApi):
    @tmp_to_root_org()
    def list(self, request, *args, **kwargs):
        nodes = self.get_nodes()
        nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        return Response(data=nodes)


class UserGrantedNodeChildrenMixin(UserGrantedNodeDispatchMixin):

    def get_nodes(self):
        user = self.user
        key = self.request.query_params.get('key')

        self.submit_update_mapping_node_task(user)

        if not key:
            nodes = get_ungranted_node_children(user)
            ungrouped_node = get_ungrouped_node(user)
            nodes = [ungrouped_node, *nodes]
        else:
            mapping_node = get_object_or_none(
                UserGrantedMappingNode, user=user, key=key
            )
            nodes = self.dispatch_node_process(key, mapping_node, None)
        return nodes

    def on_direct_granted_node(self, key, mapping_node: UserGrantedMappingNode, node: Node = None):
        return Node.objects.filter(parent_key=key)

    def on_undirect_granted_node(self, key, mapping_node: UserGrantedMappingNode, node: Node = None):
        user = self.user
        nodes = get_ungranted_node_children(user, key)
        return nodes


class UserGrantedNodesMixin:
    """
    查询用户授权的所有节点 直接授权节点 + 授权资产关联的节点
    """

    def get_nodes(self):
        user = self.user

        # 获取 `UserGrantedMappingNode` 中对应的 `Node`
        nodes = Node.objects.filter(
            mapping_nodes__user=user,
        ).annotate(**node_annotate_mapping_node).distinct()

        key2nodes_mapper = {}
        descendant_q = Q()

        for _node in nodes:
            if not is_granted(_node):
                # 未授权的节点资产数量设置为 `UserGrantedMappingNode` 中的数量
                _node.assets_amount = get_granted_assets_amount(_node)
            else:
                # 直接授权的节点
                # 增加查询后代节点的过滤条件
                descendant_q |= Q(key__startswith=f'{_node.key}:')

            key2nodes_mapper[_node.key] = _node

        if descendant_q:
            descendant_nodes = Node.objects.filter(descendant_q).annotate(**node_annotate_set_granted)
            for _node in descendant_nodes:
                key2nodes_mapper[_node.key] = _node

        all_nodes = key2nodes_mapper.values()
        return all_nodes


# ------------------------------------------
# 最终的 api
class UserGrantedNodeChildrenForAdminApi(ForAdminMixin, UserGrantedNodeChildrenMixin, NodeChildrenApi):
    pass


class MyGrantedNodeChildrenApi(ForUserMixin, UserGrantedNodeChildrenMixin, NodeChildrenApi):
    pass


class UserGrantedNodeChildrenAsTreeForAdminApi(ForAdminMixin, UserGrantedNodeChildrenMixin, NodeChildrenAsTreeApi):
    pass


class MyGrantedNodeChildrenAsTreeApi(ForUserMixin, UserGrantedNodeChildrenMixin, NodeChildrenAsTreeApi):
    pass


class UserGrantedNodesForAdminApi(ForAdminMixin, UserGrantedNodesMixin, NodeChildrenApi):
    pass


class MyGrantedNodesApi(ForUserMixin, UserGrantedNodesMixin, NodeChildrenApi):
    pass


class MyGrantedNodesAsTreeApi(ForUserMixin, UserGrantedNodesMixin, NodeChildrenAsTreeApi):
    pass

# ------------------------------------------
