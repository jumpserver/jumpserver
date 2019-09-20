# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListAPIView, get_object_or_404
)

from common.permissions import IsOrgAdminOrAppUser
from common.utils import get_logger, timeit
from ...hands import Node
from ... import serializers
from .mixin import UserAssetPermissionMixin, UserAssetTreeMixin


logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetsApi',
    'UserGrantedAssetsAsTreeApi',
    'UserGrantedNodeAssetsApi',
]


class UserGrantedAssetsApi(UserAssetPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

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
        queryset = self.util.get_assets().only(*self.only_fields)
        return queryset


class UserGrantedAssetsAsTreeApi(UserAssetTreeMixin, UserGrantedAssetsApi):
    pass


class UserGrantedNodeAssetsApi(UserGrantedAssetsApi):
    def get_queryset(self):
        node_id = self.kwargs.get("node_id")
        node = get_object_or_404(Node, pk=node_id)
        deep = self.request.query_params.get("all", "0") == "1"
        queryset = self.util.get_nodes_assets(node, deep=deep)\
            .only(*self.only_fields)
        return queryset
