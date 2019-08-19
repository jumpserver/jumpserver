# -*- coding: utf-8 -*-
#
from functools import reduce
from django.shortcuts import get_object_or_404
from django.http.response import Http404
from django.db.models import Q

from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveAPIView
)
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsValidUser, IsOrgAdminOrAppUser, IsOrgAdmin
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from ..utils import (
    ParserNode, AssetPermissionUtilV2
)
from ..hands import User, Asset, Node, SystemUser, NodeSerializer
from .. import serializers_v2 as serializers

__all__ = [
    'UserGrantedNodesApi', 'UserGrantedNodeChildrenApi',
    'UserGrantedNodeChildrenAsTreeApi', 'UserGrantedAssetApi',
]

logger = get_logger(__name__)


class UserPermissionMixin:
    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesApi(UserPermissionMixin, ListAPIView):
    """
    查询用户授权的所有节点的API
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.GrantedNodeSerializer
    pagination_class = LimitOffsetPagination
    only_fields = NodeSerializer.Meta.only_fields

    def get_queryset(self):
        user = self.get_object()
        util = AssetPermissionUtilV2(user)
        node_keys = util.get_nodes()
        queryset = Node.objects.filter(key__in=node_keys)
        return queryset


class UserGrantedNodeChildrenApi(UserGrantedNodesApi):
    def get_queryset(self):
        user = self.get_object()
        key = self.request.query_params.get("key")
        pk = self.request.query_params.get("id")
        util = AssetPermissionUtilV2(user)
        tree = util.get_user_tree()

        node = None
        if pk is not None:
            node = get_object_or_404(Node, id=id)
        elif key is not None:
            node = get_object_or_404(Node, key=key)

        if node:
            children = tree.children(node.key)
        else:
            children = tree.children(tree.root)
            if len(children) == 1:
                children.extend(tree.children(children[0].identifier))
        node_keys = [n.identifier for n in children]
        queryset = Node.objects.filter(key__in=node_keys)
        return queryset


class UserGrantedNodeChildrenAsTreeApi(UserGrantedNodeChildrenApi):
    serializer_class = TreeNodeSerializer
    only_fields = ParserNode.nodes_only_fields

    def get_serializer(self, nodes, many=True):
        queryset = []
        for node in nodes:
            data = ParserNode.parse_node_to_tree_node(node)
            queryset.append(data)
        return self.get_serializer_class()(queryset, many=many)


class UserGrantedAssetApi(UserPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    pagination_class = LimitOffsetPagination
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip']
    search_fields = filter_fields

    def filter_by_nodes(self, queryset):
        node_id = self.request.query_params.get("node")
        if not node_id:
            return queryset
        node = get_object_or_404(Node, pk=node_id)
        query_all = self.request.query_params.get("all", "0") in ["1", "true"]
        if query_all:
            pattern = '^{0}$|^{0}:'.format(node.key)
            queryset = queryset.filter(nodes__key__regex=pattern).distinct()
        else:
            queryset = queryset.filter(nodes=node)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_by_nodes(queryset)
        return queryset

    def get_queryset(self):
        user = self.get_object()
        util = AssetPermissionUtilV2(user)
        queryset = util.get_assets()
        return queryset


class UserGrantedAssetSystemUsersApi(UserPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetSystemUserSerializer
    only_fields = serializers.AssetSystemUserSerializer.Meta.only_fields

    def get_queryset(self):
        user = self.get_object()
        util = AssetPermissionUtilV2(user)
        asset_id = self.request.query_params.get("asset")
        asset = get_object_or_404(Asset, id=asset_id)
        system_users = util.get_asset_system_users(asset)



