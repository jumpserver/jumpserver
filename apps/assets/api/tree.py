# ~*~ coding: utf-8 ~*~

from django.core.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from assets.locks import NodeAddChildrenLock
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from orgs.mixins import generics
from orgs.utils import current_org
from .mixin import SerializeToTreeNodeMixin
from .. import serializers
from ..const import AllTypes
from ..models import Node

logger = get_logger(__file__)
__all__ = [
    'NodeChildrenApi',
    'NodeListAsTreeApi',
    'NodeChildrenAsTreeApi',
    'CategoryTreeApi',
]


class NodeListAsTreeApi(generics.ListAPIView):
    """
    获取节点列表树
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
    serializer_class = TreeNodeSerializer

    @staticmethod
    def to_tree_queryset(queryset):
        queryset = [node.as_tree_node() for node in queryset]
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.to_tree_queryset(queryset)
        return queryset


class NodeChildrenApi(generics.ListCreateAPIView):
    serializer_class = serializers.NodeSerializer
    search_fields = ('value',)

    instance = None
    is_initial = False

    def initial(self, request, *args, **kwargs):
        self.instance = self.get_object()
        return super().initial(request, *args, **kwargs)

    def perform_create(self, serializer):
        with NodeAddChildrenLock(self.instance):
            data = serializer.validated_data
            _id = data.get("id")
            value = data.get("value")
            if not value:
                value = self.instance.get_next_child_preset_name()
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

    def get_queryset(self):
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

    def filter_queryset(self, queryset):
        if not self.request.GET.get('search'):
            return queryset
        queryset = super().filter_queryset(queryset)
        queryset = self.model.get_ancestor_queryset(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        nodes = self.filter_queryset(self.get_queryset()).order_by('value')
        nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        assets = self.get_assets()
        data = [*nodes, *assets]
        return Response(data=data)

    def get_assets(self):
        include_assets = self.request.query_params.get('assets', '0') == '1'
        if not self.instance or not include_assets:
            return []
        assets = self.instance.get_assets().only(
            "id", "name", "address", "platform_id",
            "org_id", "is_active",
        ).prefetch_related('platform')
        return self.serialize_assets(assets, self.instance.key)


class CategoryTreeApi(SerializeToTreeNodeMixin, generics.ListAPIView):
    serializer_class = TreeNodeSerializer

    def check_permissions(self, request):
        if not request.user.has_perm('assets.view_asset'):
            raise PermissionDenied
        return True

    def list(self, request, *args, **kwargs):
        if request.query_params.get('key'):
            nodes = []
        else:
            nodes = AllTypes.to_tree_nodes()
        serializer = self.get_serializer(nodes, many=True)
        return Response(data=serializer.data)
