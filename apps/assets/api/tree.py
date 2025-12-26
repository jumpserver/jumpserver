# ~*~ coding: utf-8 ~*~

from django.db.models import Q, Count
from django.utils.translation import gettext_lazy as _
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from assets.locks import NodeAddChildrenLock
from common.exceptions import JMSException
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from orgs.mixins import generics
from orgs.utils import current_org
from orgs.models import Organization
from .mixin import SerializeToTreeNodeMixin
from .. import serializers
from ..const import AllTypes
from ..models import Node, Platform, Asset
from assets.tree.asset_tree import AssetTree


logger = get_logger(__file__)

__all__ = [
    'NodeChildrenApi',
    'NodeChildrenAsTreeApi',
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


class NodeChildrenAsTreeApi(SerializeToTreeNodeMixin, NodeChildrenApi):
    ''' 节点子节点作为树返回，
    [
      {
        "id": "",
        "name": "",
        "pId": "",
        "meta": ""
      }
    ]
    '''

    model = Node

    def list(self, request, *args, **kwargs):
        with_assets = request.query_params.get('assets', '0') == '1'
        search = request.query_params.get('search')
        key = request.query_params.get('key')

        if not with_assets:
            # 初始化资产树 - 不包含资产
            return self.init_asset_tree()
        
        if search:
            # 初始化资产搜索树 - 包含资产
            return self.search_asset_tree_with_assets(search)
        
        if key:
            # 展开资产树节点 - 包含资产
            return self.expand_asset_tree_node_with_assets(key)

        # 初始化资产树 - 包含资产
        return self.init_asset_tree_with_assets()
    
    def init_asset_tree(self):
        ''' 初始化资产树 - 不包含资产
        返回所有节点，前端本地展开和搜索
        全局组织: 不展开节点
        实体组织: 展开第1级节点
        '''
        if current_org.is_root():
            orgs = Organization.objects.all()
            expand_level = 0
        else:
            orgs = [current_org]
            expand_level = 1
        nodes = []
        for org in orgs:
            tree = AssetTree(org=org)
            _nodes = tree.get_nodes()
            nodes.extend(_nodes)
        nodes = self.serialize_nodes(
            nodes, with_asset_amount=True, expand_level=expand_level
        )
        return Response(data=nodes)
    
    def init_asset_tree_with_assets(self):
        ''' 初始化资产树 - 包含资产
        全局组织: 返回第1级节点，不返回资产，不展开
        实体组织: 返回第1级节点和第2级节点，返回第1级节点的资产，展开第1级节点
        '''
        if current_org.is_root():
            orgs = Organization.objects.all()
            node_levels = [1]
            with_assets_node_levels = None
            expand_level = 0
        else:
            orgs = [current_org]
            node_levels = [1, 2]
            with_assets_node_levels = [1]
            expand_level = 1

        nodes = []
        assets = []
        for org in orgs:
            tree = AssetTree(
                org=org, with_assets_node_levels=with_assets_node_levels
            )
            _nodes = tree.get_nodes(levels=node_levels)
            nodes.extend(_nodes)
            _assets = tree.get_assets()
            assets.extend(_assets)
        
        nodes = self.serialize_nodes(
            nodes, with_asset_amount=True, expand_level=expand_level, 
            with_assets=True
        )
        assets = self.serialize_assets(assets)
        data = [*nodes, *assets]
        return Response(data=data)
    
    def expand_asset_tree_node_with_assets(self, key):
        ''' 展开资产树节点 - 包含资产
        全局组织: 返回展开节点的直接孩子节点，返回展开节点的资产，不展开节点
        实体组织: 同上
        '''
        node = get_object_or_404(Node, key=key)
        org = node.org
        with_assets_node_id = node.id
        expand_level = 0

        tree = AssetTree(with_assets_node_id=with_assets_node_id, org=org)
        tree_node = tree.get_node(key=node.key)
        if not tree_node:
            return Response(data=[])
        _nodes = tree_node.children
        nodes = self.serialize_nodes(
            _nodes, with_asset_amount=True, expand_level=expand_level, 
            with_assets=True
        )
        _assets = tree.get_assets()
        assets = self.serialize_assets(_assets)
        data = [*nodes, *assets]
        return Response(data=data)
    
    def search_asset_tree_with_assets(self, search):
        ''' 初始化资产搜索树 - 包含资产
        不反回完整树，资产数量为0的节点不返回
        全局组织: 返回所有节点，返回所有资产，展开所有节点，限制资产总数量 1000（n 个组织，每个组织分配1000/n个资产）
        实体组织：同上，限制资产总数量 1000
        '''
        # 展开所有节点
        expand_level = 10000
        with_assets_all = True
        with_assets_limit = 1000
        full_tree = False
        assets_q_object = Q(name__icontains=search) | Q(address__icontains=search)
        if current_org.is_root():
            orgs = list(Organization.objects.all())
            with_assets_limit = max(100, with_assets_limit // max(1, orgs.count()))
        else:
            orgs = [current_org]

        nodes = []
        assets = []
        for org in orgs:
            tree = AssetTree(
                assets_q_object=assets_q_object, org=org, 
                with_assets_all=with_assets_all, 
                with_assets_limit=with_assets_limit,
                full_tree=full_tree
            )
            _nodes = tree.get_nodes()
            nodes.extend(_nodes)
            _assets = tree.get_assets()
            assets.extend(_assets)

        nodes = self.serialize_nodes(
            nodes, with_asset_amount=True, expand_level=expand_level, 
            with_assets=True
        )
        assets = self.serialize_assets(assets)
        data = [*nodes, *assets]
        return Response(data=data)

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
