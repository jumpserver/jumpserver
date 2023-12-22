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
from .mixin import SerializeToTreeNodeMixin
from .. import serializers
from ..const import AllTypes
from ..models import Node, Platform, Asset

logger = get_logger(__file__)
__all__ = [
    'NodeChildrenApi',
    'NodeChildrenAsTreeApi',
    'CategoryTreeApi',
]


class NodeChildrenApi(generics.ListCreateAPIView):
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
        with NodeAddChildrenLock(self.instance):
            data = serializer.validated_data
            _id = data.get("id")
            value = data.get("value")
            if value:
                children = self.instance.get_children()
                if children.filter(value=value).exists():
                    raise JMSException(_('The same level node name cannot be the same'))
            else:
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
        if self.instance.is_org_root():
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
        nodes = self.filter_queryset(self.get_queryset()).order_by('value')
        nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        assets = self.filter_queryset_for_assets(self.get_queryset_for_assets())
        node_key = self.instance.key if self.instance else None
        assets = self.serialize_assets(assets, node_key=node_key)
        data = [*nodes, *assets]
        return Response(data=data)


class CategoryTreeApi(SerializeToTreeNodeMixin, generics.ListAPIView):
    serializer_class = TreeNodeSerializer
    rbac_perms = {
        'GET': 'assets.view_asset',
        'list': 'assets.view_asset',
    }

    def get_assets(self):
        key = self.request.query_params.get('key')
        platform = Platform.objects.filter(id=key).first()
        if not platform:
            return []
        assets = Asset.objects.filter(platform=platform).prefetch_related('platform')
        return self.serialize_assets(assets, key)

    def list(self, request, *args, **kwargs):
        include_asset = self.request.query_params.get('assets', '0') == '1'
        # 资源数量统计可选项 (asset, account)
        count_resource = self.request.query_params.get('count_resource', 'asset')

        if not self.request.query_params.get('key'):
            nodes = AllTypes.to_tree_nodes(include_asset, count_resource=count_resource)
        elif include_asset:
            nodes = self.get_assets()
        else:
            nodes = []
        return Response(data=nodes)
