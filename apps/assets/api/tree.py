# ~*~ coding: utf-8 ~*~

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from assets.locks import NodeAddChildrenLock
from common.exceptions import JMSException
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from orgs.mixins import generics
from orgs.utils import current_org
from .mixin import NodeAssetsAmountListMixin, SerializeToTreeNodeMixin
from .. import serializers
from ..const import AllTypes
from ..models import Node, Platform, Asset
from ..utils import (
    attach_nodes_realtime_assets_amount, get_asset_tree_metrics,
    search_node_asset_tree,
)

logger = get_logger(__file__)
__all__ = [
    'NodeChildrenApi',
    'NodeChildrenAsTreeApi',
    'NodeAssetsAmountApi',
    'NodeAssetTreeSearchApi',
    'NodeTreeMetricsApi',
    'CategoryTreeApi',
]


class NodeChildrenApi(NodeAssetsAmountListMixin, generics.ListCreateAPIView):
    """
    节点的增删改查
    """
    serializer_class = serializers.NodeSerializer
    search_fields = ('value',)

    instance = None
    is_initial = False

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.instance = self.get_object()

    def perform_create(self, serializer):
        data = serializer.validated_data
        _id = data.get("id")
        value = data.get("value")
        if value:
            children = self.instance.get_children()
            if children.filter(value=value).exists():
                raise JMSException(_('The same level node name cannot be the same'))
        else:
            value = self.instance.get_next_child_preset_name()
        with NodeAddChildrenLock(self.instance):
            node = self.instance.create_child(value=value, _id=_id)
            # 避免查询 full value
            node._full_value = node.value
            serializer.instance = node

    def get_object(self):
        pk = self.kwargs.get('pk') or self.request.query_params.get('id')
        key = self.request.query_params.get("key")

        if not pk and not key:
            self.is_initial = True
            if current_org.is_root():
                node = None
            else:
                node = Node.org_root()
            return node
        if pk:
            node = get_object_or_404(Node, pk=pk)
        else:
            node = get_object_or_404(Node, key=key)
        return node

    def get_org_root_queryset(self, query_all):
        if query_all:
            return Node.objects.all()
        else:
            return Node.org_root_nodes()

    def get_base_queryset(self):
        query_all = self.request.query_params.get("all", "0") == "all"

        if self.is_initial and current_org.is_root():
            return self.get_org_root_queryset(query_all)

        if self.is_initial:
            with_self = True
        else:
            with_self = False

        if not self.instance:
            return Node.objects.none()

        if query_all:
            queryset = self.instance.get_all_children(with_self=with_self)
        else:
            queryset = self.instance.get_children(with_self=with_self)
        return queryset

    def get_queryset(self):
        return self.get_base_queryset()


class NodeChildrenAsTreeApi(SerializeToTreeNodeMixin, NodeChildrenApi):
    """
    节点子节点作为树返回，
    [
      {
        "id": "",
        "name": "",
        "pId": "",
        "meta": ""
      }
    ]

    """
    model = Node

    def get_assets_limit(self):
        raw_limit = self.request.query_params.get('assets_limit')
        if raw_limit is None:
            return None
        serializer = serializers.NodeTreeAssetsLimitQuerySerializer(data={
            'assets_limit': raw_limit,
        })
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data['assets_limit']

    def get_assets_order(self):
        serializer = serializers.NodeTreeAssetsOrderQuerySerializer(data={
            'asset_order': self.request.query_params.get('asset_order', 'name'),
        })
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data['asset_order']

    def filter_queryset(self, queryset):
        """ queryset is Node queryset """
        if not self.request.GET.get('search'):
            return queryset
        queryset = super().filter_queryset(queryset)
        queryset = self.model.get_ancestor_queryset(queryset)
        return queryset

    def get_queryset_for_assets(self):
        query_all = self.request.query_params.get("all", "0") == "all"
        include_assets = self.request.query_params.get('assets', '0') == '1'
        if not self.instance or not include_assets:
            return Asset.objects.none()
        has_assets_limit = 'assets_limit' in self.request.query_params
        if (
                not self.request.GET.get('search') and
                self.instance.is_org_root() and not has_assets_limit
        ):
            return Asset.objects.none()
        if query_all:
            assets = self.instance.get_all_assets()
        else:
            assets = self.instance.get_assets()
        return assets.only(
            "id", "name", "address", "platform_id",
            "org_id", "is_active", 'comment'
        ).prefetch_related('platform')

    def filter_queryset_for_assets(self, assets):
        search = self.request.query_params.get('search')
        if search:
            q = Q(name__icontains=search) | Q(address__icontains=search)
            assets = assets.filter(q)
        return assets

    def list(self, request, *args, **kwargs):
        include_assets = request.query_params.get('assets', '0') == '1'
        with_asset_amount = request.query_params.get('asset_amount', '1') == '1'
        query_all = request.query_params.get('all', '0') == 'all'
        compact = request.query_params.get('compact', '0') == '1'
        assets_limit = self.get_assets_limit()
        assets_order = self.get_assets_order()

        nodes = self.filter_queryset(self.get_base_queryset())
        nodes = nodes.order_by('value')

        if (
                compact and query_all and not include_assets and
                not with_asset_amount and assets_limit is None
        ):
            rows = nodes.values_list('id', 'key', 'value', 'parent_key')
            return Response(data=self.serialize_compact_nodes(rows))

        nodes = nodes.only(
            'id', 'key', 'value', 'parent_key', 'org_id', 'assets_amount'
        )

        if query_all and not include_assets:
            # The complete response already contains every descendant. Derive
            # leaf state in linear time and avoid one EXISTS subquery per node.
            nodes = list(nodes)
            parent_keys = {node.parent_key for node in nodes if node.parent_key}
            for node in nodes:
                node.has_children = node.key in parent_keys
        else:
            nodes = list(nodes.with_has_children(include_assets=include_assets))

        if with_asset_amount:
            nodes = attach_nodes_realtime_assets_amount(nodes)

        nodes = self.serialize_nodes(nodes, with_asset_amount=with_asset_amount)
        assets = self.filter_queryset_for_assets(self.get_queryset_for_assets())
        assets_truncated = False
        if assets_limit is not None:
            order_fields = (
                ('address', 'name', 'id')
                if assets_order == 'address'
                else ('name', 'address', 'id')
            )
            assets = assets.order_by(*order_fields)
            assets = list(assets[:assets_limit + 1])
            assets_truncated = len(assets) > assets_limit
            assets = assets[:assets_limit]
        node_key = self.instance.key if self.instance else None
        assets = self.serialize_assets(assets, node_key=node_key)
        data = [*nodes, *assets]
        if assets_limit is not None:
            return Response({
                'results': data,
                'assets_truncated': assets_truncated,
                'assets_limit': assets_limit,
            })
        return Response(data=data)


class NodeAssetsAmountApi(generics.CreateAPIView):
    """Return exact direct or subtree asset counts for a bounded node batch."""

    serializer_class = serializers.NodeAssetsAmountQuerySerializer
    rbac_perms = {
        'POST': 'assets.view_node',
    }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        node_ids = serializer.validated_data['node_ids']
        include_descendants = serializer.validated_data['include_descendants']
        fresh = serializer.validated_data['fresh']

        nodes = attach_nodes_realtime_assets_amount(
            Node.objects.filter(id__in=node_ids).only('id', 'key', 'org_id'),
            include_descendants=include_descendants,
            fresh=fresh,
        )
        nodes_by_id = {str(node.id): node for node in nodes}
        results = []
        for node_id in node_ids:
            node = nodes_by_id.get(str(node_id))
            if not node:
                continue
            results.append({
                'id': str(node.id),
                'key': node.key,
                'assets_amount': node.assets_amount_realtime,
            })
        return Response({'results': results})


class NodeAssetTreeSearchApi(generics.ListAPIView):
    """Search nodes or assets and return the paths required by a tree."""

    model = Node
    serializer_class = serializers.NodeAssetTreeSearchQuerySerializer
    rbac_perms = {
        'GET': 'assets.view_asset',
    }

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        node_id = data.get('node_id')
        scope_node = None
        if node_id:
            scope_node = get_object_or_404(Node, id=node_id)
        result = search_node_asset_tree(
            search=data['search'],
            target=data['target'],
            limit=data['limit'],
            scope_node=scope_node,
        )
        return Response(result)


class NodeTreeMetricsApi(generics.CreateAPIView):
    """Return asset metrics for a bounded visible node/asset batch."""

    model = Node
    serializer_class = serializers.NodeTreeMetricsQuerySerializer
    rbac_perms = {
        'POST': 'assets.view_asset',
    }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        scope_node = None
        if data.get('node_id'):
            scope_node = get_object_or_404(Node, id=data['node_id'])
        results = get_asset_tree_metrics(
            items=data['items'],
            metric=data['metric'],
            search=data.get('search'),
            scope_node=scope_node,
            fresh=data['fresh'],
        )
        return Response({
            'metric': data['metric'],
            'results': results,
        })


class CategoryTreeApi(SerializeToTreeNodeMixin, generics.ListAPIView):
    serializer_class = TreeNodeSerializer
    rbac_perms = {
        'GET': 'assets.view_asset',
        'list': 'assets.view_asset',
    }
    queryset = Node.objects.none()

    def get_assets(self):
        key = self.request.query_params.get('key')
        platform = Platform.objects.filter(id=key).first()
        if not platform:
            return []
        assets = Asset.objects.filter(platform=platform).prefetch_related('platform')
        return self.serialize_assets(assets, key)

    def list(self, request, *args, **kwargs):
        include_asset = self.request.query_params.get('assets', '0') == '1'
        # 资源数量统计可选项 (asset, account, none)
        count_resource = self.request.query_params.get('count_resource', 'asset')

        if not self.request.query_params.get('key'):
            nodes = AllTypes.to_tree_nodes(include_asset, count_resource=count_resource)
        elif include_asset:
            nodes = self.get_assets()
        else:
            nodes = []
        return Response(data=nodes)
