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
        with_assets = request.query_params.get('assets', '0') == '1'
        search = request.query_params.get('search')
        node_key = request.query_params.get('key')
        asset_category = request.query_params.get('category')
        asset_type = request.query_params.get('type')
        # test
        if search:
            search_list = search.split()
            for s in search_list:
                node = s.split('node:')
                if len(node) == 2:
                    search = node[1]
                    with_assets = False
                    break

                asset = s.split('asset:')
                if len(asset) == 2:
                    search = asset[1]
                    continue
                asset_category = s.split('category:')
                if len(asset_category) == 2:
                    asset_category = asset_category[1]
                    continue
                asset_type = s.split('type:')
                if len(asset_type) == 2:
                    asset_type = asset_type[1]
                    continue

        if node_key:
            with_assets = True
            search = None
            asset_category = None
            asset_type = None

        if with_assets:
            if node_key:
                return self.expand_tree_node_with_assets(
                    node_key, asset_category, asset_type
                )
            elif search:
                # search assets
                return self.search_user_perm_tree_with_assets(
                    search, asset_category, asset_type
                )
            else:
                return self.init_user_perm_tree_with_assets(
                    asset_category, asset_type
                )
        else:
            if search:
                # search nodes
                return self.search_user_perm_tree(search)
            else:
                return self.init_user_perm_tree()
    
    def init_user_perm_tree(self):
        ''' 初始化用户权限树 - 不包含资产
        前端搜索

        全局组织: 返回所有节点，不返回资产，不展开节点
        实体组织：返回所有节点，不返回资产，展开第1级节点

        返回收藏节点
        返回未分组节点 (如果需要)
        '''
        if current_org.is_root():
            orgs = self.user.orgs.all()
            expand_level = 0
        else:
            orgs = self.user.orgs.filter(id=current_org.id)
            expand_level = 1
        
        if not orgs.exists():
            return Response(data=[])
        
        nodes = []
        for org in orgs:
            tree = UserPermTree(user=self.user, org=org)
            _nodes = tree.get_nodes()
            nodes.extend(_nodes)
        nodes = self.serialize_nodes(
            nodes, with_asset_amount=True, expand_level=expand_level
        )
        data = nodes
        data = self.add_favorites_and_ungrouped_node(data, with_assets=False)
        return Response(data=data)
    
    def search_user_perm_tree(self, search):
        ''' 搜索用户授权树 - 不包含资产
        全局组织: 返回所有匹配节点以及祖先节点，不返回匹配节点的子孙节点，不返回资产，展开所有祖先节点，不展开匹配节点
        实体组织: 同上
        '''
        if current_org.is_root():
            orgs = self.user.orgs.all()
        else:
            orgs = self.user.orgs.filter(id=current_org.id)
        
        search_nodes = []
        nodes_ancestors = []
        for org in orgs:
            tree = UserPermTree(user=self.user, org=org)
            _search_nodes = tree.search_nodes(search, only_top_level=True)
            # tree.remove_nodes_descendants(_search_nodes)
            _nodes_ancestors = tree.get_nodes_ancestors(_search_nodes)
            search_nodes.extend(_search_nodes)
            nodes_ancestors.extend(_nodes_ancestors)
        
        # 不展开搜索节点
        expand_level = 0
        # 如果有资产，则允许展开 is_parent=True 的节点
        with_assets = True
        serialized_search_nodes = self.serialize_nodes(
            search_nodes, with_asset_amount=True, expand_level=expand_level, 
            with_assets=with_assets
        )
        # 展开所有祖先节点
        expand_level = 10000
        serialized_nodes_ancestors = self.serialize_nodes(
            nodes_ancestors, with_asset_amount=True, expand_level=expand_level
        )
        data = [*serialized_nodes_ancestors, *serialized_search_nodes]
        return Response(data=data)

    def init_user_perm_tree_with_assets(self, asset_category=None, asset_type=None):
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
        
        nodes = []
        assets = []

        for org in orgs:
            tree = UserPermTree(
                user=self.user, 
                asset_category=asset_category, asset_type=asset_type, org=org, 
                with_assets_node_levels=with_assets_node_levels
            )
            _nodes = tree.get_nodes(levels=nodes_level)
            nodes.extend(_nodes)
            _assets = tree.get_assets()
            assets.extend(_assets)
        
        nodes = self.serialize_nodes(
            nodes, with_asset_amount=True, expand_level=expand_level, with_assets=True
        )
        assets = self.serialize_assets(assets)
        data = [*nodes, *assets]
        data = self.add_favorites_and_ungrouped_node(data, with_assets=True)
        return Response(data=data)
    
    def expand_tree_node_with_assets(self, node_key, asset_category=None, asset_type=None):
        ''' 展开用户权限资产树节点 - 包含资产
        全局组织: 返回展开节点的直接孩子节点，返回展开节点的资产，不展开其他节点
        实体组织: 同上
        '''
        expand_level = 0
        node = get_object_or_404(Node, key=node_key)
        org = self.user.orgs.filter(id=node.org_id).first()
        if not org:
            return Response(data=[])

        tree = UserPermTree(
            user=self.user, 
            asset_category=asset_category, asset_type=asset_type,
            org=node.org, with_assets_node_id=node.id
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
    
    def search_user_perm_tree_with_assets(self, search, asset_category=None, asset_type=None):
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
                user=self.user, assets_q_object=assets_q_object, 
                org=org, asset_category=asset_category, asset_type=asset_type,
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

    def add_favorites_and_ungrouped_node(self, data: list, with_assets=False):
        # 未分组节点和资产
        u_node, u_assets = self.get_ungrouped_node_if_need()
        if u_node:
            data.insert(0, u_node)
            data.extend(u_assets)

        # 收藏节点和资产
        f_node, f_assets = self.get_favorite_node()
        if f_node:
            data.insert(0, f_node)
            data.extend(f_assets)
        return data
    
    def get_favorite_node(self, with_assets=False):
        assets = UserPermUtil.get_favorite_assets(self.user)
        assets_amount = assets.count()
        node = PermTreeNode(
            _id=PermTreeNode.SpecialKey.FAVORITE.value,
            key=PermTreeNode.SpecialKey.FAVORITE.value,
            value=PermTreeNode.SpecialKey.FAVORITE.label,
            assets_amount=assets_amount
        )
        node.assets_amount_total = assets_amount
        nodes = self.serialize_nodes(
            [node], with_asset_amount=True, expand_level=0, with_assets=with_assets
        )
        serialized_node = nodes[0] if nodes else None

        if not with_assets:
            return serialized_node, []

        if assets_amount == 0:
            return serialized_node, []
        
        assets = list(assets.values(*AssetTreeNodeAsset.model_values))
        assets = node.init_assets(assets)
        serialized_assets = self.serialize_assets(assets)
        return serialized_node, serialized_assets

    def get_ungrouped_node_if_need(self, with_assets=False):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return None, []

        if current_org.is_root():
            return None, []

        org = self.user.orgs.filter(id=current_org.id).first()
        if not org:
            return None, []

        _util = UserPermUtil(user=self.user, org=org)
        assets = _util.get_ungrouped_assets()
        assets_amount = assets.count()
        node = PermTreeNode(
            _id=PermTreeNode.SpecialKey.UNGROUPED.value,
            key=PermTreeNode.SpecialKey.UNGROUPED.value,
            value=PermTreeNode.SpecialKey.UNGROUPED.label,
            assets_amount=assets_amount
        )
        node.assets_amount_total = assets_amount
        nodes = self.serialize_nodes(
            [node], with_asset_amount=True, expand_level=0, with_assets=with_assets
        )
        serialized_node = nodes[0] if nodes else None

        if not with_assets:
            return serialized_node, []

        if assets_amount == 0:
            return serialized_node, []

        assets = assets.values(*AssetTreeNodeAsset.model_values)
        assets = node.init_assets(list(assets))
        serialized_assets = self.serialize_assets(assets)
        return serialized_node, serialized_assets