# -*- coding: utf-8 -*-
#
from ..mixin import UserPermissionMixin
from ...utils import AssetPermissionUtilV2, ParserNode
from ...hands import Node
from common.tree import TreeNodeSerializer


class UserAssetPermissionMixin(UserPermissionMixin):
    util = None

    def initial(self, *args, **kwargs):
        super().initial(*args, *kwargs)
        cache_policy = self.request.query_params.get('cache_policy', '0')
        self.util = AssetPermissionUtilV2(self.obj, cache_policy=cache_policy)


class UserNodeTreeMixin:
    serializer_class = TreeNodeSerializer
    nodes_only_fields = ParserNode.nodes_only_fields
    tree = None

    def parse_nodes_to_queryset(self, nodes):
        nodes = nodes.only(*self.nodes_only_fields)
        _queryset = []

        tree = self.util.get_user_tree()
        for node in nodes:
            assets_amount = tree.assets_amount(node.key)
            if assets_amount == 0 and node.key != Node.empty_key:
                continue
            node._assets_amount = assets_amount
            data = ParserNode.parse_node_to_tree_node(node)
            _queryset.append(data)
        return _queryset

    def get_serializer_queryset(self, queryset):
        queryset = self.parse_nodes_to_queryset(queryset)
        return queryset

    def get_serializer(self, queryset, many=True, **kwargs):
        queryset = self.get_serializer_queryset(queryset)
        queryset.sort()
        return super().get_serializer(queryset, many=many, **kwargs)


class UserAssetTreeMixin:
    serializer_class = TreeNodeSerializer
    nodes_only_fields = ParserNode.assets_only_fields

    @staticmethod
    def parse_assets_to_queryset(assets, node):
        _queryset = []
        for asset in assets:
            data = ParserNode.parse_asset_to_tree_node(node, asset)
            _queryset.append(data)
        return _queryset

    def get_serializer_queryset(self, queryset):
        queryset = queryset.only(*self.nodes_only_fields)
        _queryset = self.parse_assets_to_queryset(queryset, None)
        return _queryset

    def get_serializer(self, queryset, many=True, **kwargs):
        queryset = self.get_serializer_queryset(queryset)
        queryset.sort()
        return super().get_serializer(queryset, many=many, **kwargs)
