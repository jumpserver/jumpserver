# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404

from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveAPIView
)
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsValidUser, IsOrgAdminOrAppUser, IsOrgAdmin
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from ..utils import (
    AssetPermissionUtil, ParserNode, AssetPermissionUtilV2
)
from .. import const
from ..hands import User, Asset, Node, SystemUser, NodeSerializer
from .. import serializers


class UserGrantedNodesApi(ListAPIView):
    """
    查询用户授权的所有节点的API
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = NodeSerializer
    pagination_class = LimitOffsetPagination
    only_fields = NodeSerializer.Meta.only_fields

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_nodes(self, nodes_with_assets):
        node_keys = [n["key"] for n in nodes_with_assets]
        nodes = Node.objects.filter(key__in=node_keys).only(
            *self.only_fields
        )
        nodes_map = {n.key: n for n in nodes}

        _nodes = []
        for n in nodes_with_assets:
            key = n["key"]
            node = nodes_map.get(key)
            node._assets_amount = n["assets_amount"]
            _nodes.append(node)
        return _nodes

    def get_serializer(self, nodes_with_assets, many=True):
        nodes = self.get_nodes(nodes_with_assets)
        return super().get_serializer(nodes, many=True)

    def get_queryset(self):
        user = self.get_object()
        self.util = AssetPermissionUtilV2(user)
        nodes_with_assets = self.util.get_nodes_with_assets()
        return nodes_with_assets

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()
