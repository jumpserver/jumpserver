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
        search = request.query_params.get('search')
        with_assets = request.query_params.get('assets', '0') == '1'
        with_asset_amount = request.query_params.get('asset_amount', '1') == '1'
        with_asset_amount = True
        nodes, assets, expand_level = self.get_nodes_assets(search, with_assets)
        nodes = self.serialize_nodes(nodes, with_asset_amount=with_asset_amount, expand_level=expand_level)
        assets = self.serialize_assets(assets)
        data = [*nodes, *assets]
        return Response(data=data)

    def get_nodes_assets(self, search, with_assets):
        #
        # 资产管理-节点树
        #

        # 全局组织: 初始化节点树, 返回所有节点, 不包含资产, 不展开节点
        # 实体组织: 初始化节点树, 返回所有节点, 不包含资产, 展开一级节点
        # 前端搜索
        if not with_assets:
            if current_org.is_root():
                orgs = Organization.objects.all()
                expand_level = 0
            else:
                orgs = [current_org]
                expand_level = 1
            
            nodes = []
            assets = []
            for org in orgs:
                tree = AssetTree(org=org)
                org_nodes = tree.get_nodes()
                nodes.extend(org_nodes)
            return nodes, assets, expand_level
        
        #
        # 权限管理、账号发现、风险检测 - 资产节点树
        #

        # 全局组织: 搜索资产, 生成资产节点树, 过滤每个组织前 1000 个资产, 展开所有节点
        # 实体组织: 搜索资产, 生成资产节点树, 过滤前 1000 个资产, 展开所有节点
        if search:
            if current_org.is_root():
                orgs = list(Organization.objects.all())
            else:
                orgs = [current_org]
            nodes = []
            assets = []
            assets_q_object = Q(name__icontains=search) | Q(address__icontains=search)
            with_assets_limit = 1000 / len(orgs)
            for org in orgs:
                tree = AssetTree(
                    assets_q_object=assets_q_object, org=org, 
                    with_assets=True, with_assets_limit=with_assets_limit, full_tree=False
                )
                nodes.extend(tree.get_nodes())
                assets.extend(tree.get_assets())
            expand_level = 10000  # search 时展开所有节点
            return nodes, assets, expand_level
        
        # 全局组织: 展开某个节点及其资产
        # 实体组织: 展开某个节点及其资产
        # 实体组织: 初始化资产节点树, 自动展开根节点及其资产, 所以节点要包含自己 (特殊情况)
        if self.instance:
            nodes = []
            tree = AssetTree(with_assets_node_id=self.instance.id, org=self.instance.org)
            nodes_with_self = False
            if not current_org.is_root() and self.instance.is_org_root():
                nodes_with_self = True
            nodes = tree.get_node_children(key=self.instance.key, with_self=nodes_with_self)
            assets = tree.get_assets()
            expand_level = 1  # 默认只展开第一级
            return nodes, assets, expand_level
        
        # 全局组织: 初始化资产节点树, 仅返回各组织根节点, 不展开
        orgs = Organization.objects.all()
        nodes = []
        assets = []
        for org in orgs:
            tree = AssetTree(org=org, with_assets=False)
            if not tree.root:
                continue
            nodes.append(tree.root)
        expand_level = 0  # 默认不展开节点
        return nodes, assets, expand_level


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
