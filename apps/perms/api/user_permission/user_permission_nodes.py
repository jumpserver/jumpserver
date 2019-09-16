# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListAPIView, get_object_or_404
)

from common.permissions import IsOrgAdminOrAppUser
from common.utils import get_logger
from ...hands import Node, NodeSerializer
from ... import serializers
from .mixin import UserNodeTreeMixin, UserAssetPermissionMixin


logger = get_logger(__name__)

__all__ = [
    'UserGrantedNodesApi',
    'UserGrantedNodesAsTreeApi',
    'UserGrantedNodeChildrenApi',
    'UserGrantedNodeChildrenAsTreeApi',
]


class UserGrantedNodesApi(UserAssetPermissionMixin, ListAPIView):
    """
    查询用户授权的所有节点的API
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.NodeGrantedSerializer
    nodes_only_fields = NodeSerializer.Meta.only_fields

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.serializer_class == serializers.NodeGrantedSerializer:
            context["tree"] = self.tree
        return context

    def get_queryset(self):
        node_keys = self.util.get_nodes()
        queryset = Node.objects.filter(key__in=node_keys)\
            .only(*self.nodes_only_fields)
        return queryset


class UserGrantedNodesAsTreeApi(UserNodeTreeMixin, UserGrantedNodesApi):
    pass


class UserGrantedNodeChildrenApi(UserGrantedNodesApi):
    node = None
    root_keys = None  # 如果是第一次访问，则需要把二级节点添加进去，这个 roots_keys

    def get(self, request, *args, **kwargs):
        key = self.request.query_params.get("key")
        pk = self.request.query_params.get("id")

        node = None
        if pk is not None:
            node = get_object_or_404(Node, id=pk)
        elif key is not None:
            node = get_object_or_404(Node, key=key)
        self.node = node
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if self.node:
            children = self.tree.children(self.node.key)
        else:
            children = self.tree.children(self.tree.root)
            # 默认打开组织节点下的节点
            self.root_keys = [child.identifier for child in children]
            for key in self.root_keys:
                children.extend(self.tree.children(key))
        node_keys = [n.identifier for n in children]
        queryset = Node.objects.filter(key__in=node_keys)
        return queryset


class UserGrantedNodeChildrenAsTreeApi(UserNodeTreeMixin, UserGrantedNodeChildrenApi):
    pass
