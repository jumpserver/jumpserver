from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from common.utils import get_logger, timeit
from orgs.utils import current_org
from assets.api import SerializeToTreeNodeMixin
from assets.models import Node, FavoriteAsset, Asset
from assets.tree.asset_tree import AssetTreeNodeAsset
from perms.tree import UserPermTree, PermTreeNode
from perms.utils.utils import UserPermUtil

from .mixin import SelfOrPKUserMixin

logger = get_logger(__name__)

__all__ = [
    'UserPermNodeChildrenAsTreeApi'
]


class UserPermNodeChildrenAsTreeApi(SelfOrPKUserMixin, SerializeToTreeNodeMixin, ListAPIView):

    @timeit
    def list(self, request, *args, **kwargs):
        search = request.query_params.get('search')
        key = request.query_params.get('key')
        if search:
            return self.search_user_perm_tree_with_assets(search)

        if key:
            return self.expand_tree_node_with_assets(key)

        return self.init_user_perm_tree_with_assets()

    def init_user_perm_tree_with_assets(self):
        ''' 初始化用户权限资产树 - 包含资产
        全局组织: 返回第1级节点，不返回资产，不展开节点
        实体组织：返回第1级和第2级节点，返回第1级节点的资产，展开第1级节点

        返回收藏节点和资产
        返回未分组节点和资产 (如果需要)
        '''

        if current_org.is_root():
            orgs = self.user.orgs.all()
            nodes_level = [1]
            with_assets_node_levels = None
            expand_level = 0
        else:
            orgs = self.user.orgs.filter(id=current_org.id)
            nodes_level = [1, 2]
            with_assets_node_levels = [1]
            expand_level = 1
        
        if not orgs.exists():
            return Response(data=[])
        
        # 收藏节点和资产
        f_node, f_assets = self.get_favorite_node_with_assets()
        f_nodes = []
        if f_node:
            f_nodes = self.serialize_nodes(
                [f_node], with_asset_amount=True, expand_level=0, with_assets=True
            )
        
        # 未分组节点和资产
        u_node, u_assets = self.get_ungrouped_node_with_assets_if_need()
        u_nodes = []
        if u_node:
            u_nodes = self.serialize_nodes(
                [u_node], with_asset_amount=True, expand_level=0, with_assets=True
            )
        
        nodes = []
        assets = []

        for org in orgs:
            tree = UserPermTree(
                user=self.user, org=org, with_assets_node_levels=with_assets_node_levels
            )
            _nodes = tree.get_nodes(levels=nodes_level)
            nodes.extend(_nodes)
            _assets = tree.get_assets()
            assets.extend(_assets)
        
        nodes = self.serialize_nodes(
            nodes, with_asset_amount=True, expand_level=expand_level, with_assets=True
        )
        assets = [*f_assets, *u_assets, *assets]
        assets = self.serialize_assets(assets)
        data = [*f_nodes, *u_nodes, *nodes, *assets]
        return Response(data)
    
    def expand_tree_node_with_assets(self, key):
        ''' 展开用户权限资产树节点 - 包含资产
        全局组织: 返回展开节点的直接孩子节点，返回展开节点的资产，不展开其他节点
        实体组织: 同上
        '''
        expand_level = 0
        node = get_object_or_404(Node, key=key)
        org = self.user.orgs.filter(id=node.org_id).first()
        if not org:
            return Response(data=[])

        tree = UserPermTree(
            user=self.user, org=node.org, with_assets_node_id=node.id
        )
        tree_node = tree.get_node(node.key)
        if not tree_node:
            return Response(data=[])
        
        _nodes = tree_node.children
        nodes = self.serialize_nodes(
            _nodes, with_asset_amount=True, expand_level=expand_level, with_assets=True
        )
        _assets = tree.get_assets()
        assets = self.serialize_assets(_assets)
        data = [*nodes, *assets]
        return Response(data=data)
    
    def search_user_perm_tree_with_assets(self, search):
        ''' 初始化用户权限资产搜索树 - 包含资产 
        全局组织: 返回所有节点，返回所有资产，展开所有节点，搜索资产 (最大 1000， n 个组织，每个组织分配1000/n个资产)
        实体组织: 同上，最大资产数 1000
        '''
        expand_level = 10000
        with_assets_all = True
        with_assets_limit = 1000
        if current_org.is_root():
            orgs = self.user.orgs.all()
            with_assets_limit = max(100, with_assets_limit // max(1, orgs.count()))
        else:
            orgs = self.user.orgs.filter(id=current_org.id)

        if not orgs.exists():
            return Response(data=[])

        assets_q_object = Q(name__icontains=search) | Q(address__icontains=search)
        nodes = []
        assets = []
        for org in orgs:
            tree = UserPermTree(
                user=self.user, assets_q_object=assets_q_object, org=org, 
                with_assets_all=with_assets_all,
                with_assets_limit=with_assets_limit
            )
            _nodes = tree.get_nodes()
            nodes.extend(_nodes)
            _assets = tree.get_assets()
            assets.extend(_assets)

        nodes = self.serialize_nodes(
            nodes, with_asset_amount=True, expand_level=expand_level, with_assets=True
        )
        assets = self.serialize_assets(assets)
        data = [*nodes, *assets]
        return Response(data=data)
    
    def get_favorite_node_with_assets(self):
        asset_ids = FavoriteAsset.get_user_favorite_asset_ids(self.user)
        assets_amount = len(asset_ids)
        node = PermTreeNode(
            _id='favorite',
            key='favorite',
            value=_('Favorite'),
            assets_amount=assets_amount
        )
        node.assets_amount_total = assets_amount

        if not asset_ids:
            return node, []
        
        assets = Asset.objects.filter(id__in=asset_ids).values(*AssetTreeNodeAsset.model_values)
        assets = list(assets)
        node.init_assets(assets)
        assets = node.get_assets()
        return node, assets

    def get_ungrouped_node_with_assets_if_need(self):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return None, []

        if current_org.is_root():
            return None, []

        org = self.user.orgs.filter(id=current_org.id).first()
        if not org:
            return None, []

        _util = UserPermUtil(user=self.user, org=org)
        direct_asset_ids = _util._user_direct_asset_ids
        assets_amount = len(direct_asset_ids)
        node = PermTreeNode(
            _id='ungrouped',
            key='ungrouped',
            value=_('Ungrouped'),
            assets_amount=assets_amount
        )
        node.assets_amount_total = assets_amount
        if not direct_asset_ids:
            return node, []
        assets = Asset.objects.filter(id__in=direct_asset_ids).values(*AssetTreeNodeAsset.model_values)
        node.init_assets(list(assets))
        assets = node.get_assets()
        return node, assets
