# -*- coding: utf-8 -*-
#
from common.utils import get_logger
from ...utils import ParserNode
from .mixin import UserAssetTreeMixin
from ...hands import Node
from .user_permission_nodes import UserGrantedNodesAsTreeApi
from .user_permission_nodes import UserGrantedNodeChildrenAsTreeApi


logger = get_logger(__name__)

__all__ = [
    'UserGrantedNodesAsTreeApi',
    'UserGrantedNodesWithAssetsAsTreeApi',
    'UserGrantedNodeChildrenAsTreeApi',
    'UserGrantedNodeChildrenWithAssetsAsTreeApi',
]


class UserGrantedNodesWithAssetsAsTreeApi(UserGrantedNodesAsTreeApi):
    def get_serializer_queryset(self, queryset):
        _queryset = super().get_serializer_queryset(queryset)
        for node in queryset:
            assets = self.util.get_nodes_assets(node)
            _queryset.extend(
                UserAssetTreeMixin.parse_assets_to_queryset(assets, node)
            )
        return _queryset


class UserGrantedNodeChildrenWithAssetsAsTreeApi(UserGrantedNodeChildrenAsTreeApi):
    nodes_only_fields = ParserNode.nodes_only_fields
    assets_only_fields = ParserNode.assets_only_fields

    def get_serializer_queryset(self, queryset):
        _queryset = super().get_serializer_queryset(queryset)
        nodes = []
        if self.node:
            nodes.append(self.node)
        elif self.root_keys:
            nodes = Node.objects.filter(key__in=self.root_keys)

        for node in nodes:
            assets = self.util.get_nodes_assets(node).only(
                *self.assets_only_fields
            )
            _queryset.extend(
                UserAssetTreeMixin.parse_assets_to_queryset(assets, node)
            )
        return _queryset
