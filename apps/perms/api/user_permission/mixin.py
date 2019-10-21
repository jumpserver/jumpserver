# -*- coding: utf-8 -*-
#
from common.utils import lazyproperty
from common.tree import TreeNodeSerializer
from ..mixin import UserPermissionMixin
from ...utils import AssetPermissionUtilV2, ParserNode
from ...hands import Node, Asset


class UserAssetPermissionMixin(UserPermissionMixin):
    util = None

    @lazyproperty
    def util(self):
        cache_policy = self.request.query_params.get('cache_policy', '0')
        system_user_id = self.request.query_params.get("system_user")
        util = AssetPermissionUtilV2(self.obj, cache_policy=cache_policy)
        if system_user_id:
            util.filter_permissions(system_users=system_user_id)
        return util

    @lazyproperty
    def tree(self):
        return self.util.get_user_tree()


class UserNodeTreeMixin:
    serializer_class = TreeNodeSerializer
    nodes_only_fields = ParserNode.nodes_only_fields

    def parse_nodes_to_queryset(self, nodes):
        nodes = nodes.only(*self.nodes_only_fields)
        _queryset = []

        for node in nodes:
            assets_amount = self.tree.valid_assets_amount(node.key)
            if assets_amount == 0 and not node.key.startswith('-'):
                continue
            node.assets_amount = assets_amount
            data = ParserNode.parse_node_to_tree_node(node)
            _queryset.append(data)
        return _queryset

    def get_serializer_queryset(self, queryset):
        queryset = self.parse_nodes_to_queryset(queryset)
        return queryset

    def get_serializer(self, queryset=None, many=True, **kwargs):
        if queryset is None:
            queryset = Node.objects.none()
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

    def get_serializer(self, queryset=None, many=True, **kwargs):
        if queryset is None:
            queryset = Asset.objects.none()
        queryset = self.get_serializer_queryset(queryset)
        queryset.sort()
        return super().get_serializer(queryset, many=many, **kwargs)
