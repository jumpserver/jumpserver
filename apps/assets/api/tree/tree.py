# ~*~ coding: utf-8 ~*~

from django.utils.translation import gettext_lazy as _
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from assets.locks import NodeAddChildrenLock
from assets.models import Platform
from common.exceptions import JMSException
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from orgs.mixins import generics
from orgs.utils import current_org, tmp_to_org
from ..mixin import SerializeToTreeNodeMixin
from .const import RenderTreeView
from ... import serializers
from ...const import AllTypes
from ...models import Node, Platform, Asset
from assets.tree.node_tree import AssetNodeTree
# from assets.tree.category import AssetTreeCategoryView
from .base import AbstractAssetTreeAPI


logger = get_logger(__file__)

__all__ = [
    'NodeChildrenApi',
    'AssetTreeAPI',
    'CategoryTreeApi',
]


class NodeChildrenApi(generics.ListCreateAPIView):
    ''' 节点的增删改查 '''
    serializer_class = serializers.NodeSerializer
    search_fields = ('value',)

    instance = None
    is_initial = False
    perm_model = Node

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.initial_org_root_node_if_need()
        self.instance = self.get_object()
    
    def initial_org_root_node_if_need(self):
        if current_org.is_root():
            return
        Node.org_root()

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


class AssetTreeAPI(AbstractAssetTreeAPI):

    rbac_perms = {
        'list': 'assets.view_asset',
        'GET': 'assets.view_asset',
        'OPTIONS': 'assets.view_asset',
    }

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.initial_org_root_node_if_need()

    def initial_org_root_node_if_need(self):
        if current_org.is_root():
            orgs = self.request.user.orgs.all()
        else:
            orgs = [current_org]

        for org in orgs:
            with tmp_to_org(org):
                Node.org_root()

    def get_tree_user(self):
        return self.request.user

    def _get_asset_tree(self, tree_view: RenderTreeView, **kwargs):
        if tree_view.is_node_view:
            tree = AssetNodeTree(**kwargs)
        elif tree_view.is_category_view:
            raise ValueError('Category tree view is not implemented yet')
            # tree = AssetTreeCategoryView(**kwargs)
        else:
            raise ValueError(f'Unsupported tree view: {tree_view}')
        return tree


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
        # 资源数量统计可选项 (asset, account)
        count_resource = self.request.query_params.get('count_resource', 'asset')

        if not self.request.query_params.get('key'):
            nodes = AllTypes.to_tree_nodes(include_asset, count_resource=count_resource)
        elif include_asset:
            nodes = self.get_assets()
        else:
            nodes = []
        return Response(data=nodes)
