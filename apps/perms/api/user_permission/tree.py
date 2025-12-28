from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.conf import settings


from common.utils import get_logger, timeit
from assets.api.tree import AbstractAssetTreeAPI
from assets.tree.asset_tree import AssetTreeNodeAsset
from perms.tree import UserPermAssetTree, UserPermAssetTreeNode
from perms.utils.utils import UserPermedAssetUtil

from .mixin import SelfOrPKUserMixin

logger = get_logger(__name__)

__all__ = [
    'UserPermedAssetTreeAPI'
]


class UserPermedAssetTreeAPI(SelfOrPKUserMixin, AbstractAssetTreeAPI):

    def get_tree_user(self):
        return self.user

    def get_org_asset_tree(self, **kwargs) -> UserPermAssetTree:
        # 重写父类方法，返回用户授权的组织资产树
        return self.get_user_org_asset_tree(**kwargs)

    def get_user_org_asset_tree(self, **kwargs) -> UserPermAssetTree:
        # 获取用户授权的组织资产树
        tree = UserPermAssetTree(user=self.user, **kwargs)
        return tree
    
    def _render_asset_tree(self, **kwargs):
        # 重写父类方法，返回特殊节点
        # 特殊节点如：收藏夹、未分组节点
        data = super()._render_asset_tree(**kwargs)
        expand_node_key = kwargs.pop('expand_node_key', None)
        if expand_node_key:
            # 展开其他节点时，不返回特殊节点
            # 特殊节点不允许异步展开
            return data
        special_nodes = self.get_special_nodes(**kwargs)
        data = special_nodes + data
        return data
    
    def render_node_tree(self, **kwargs):
        # 重写父类方法，返回特殊节点
        data = super().render_node_tree(**kwargs)
        special_nodes = self.get_special_nodes(**kwargs)
        data = special_nodes + data
        return data
    
    @timeit
    def get_special_nodes(self, search_asset=None, search_node=None, 
                          asset_category=None, asset_type=None, with_asset_amount=True):
        # 获取特殊节点数据
        # 特殊节点如：收藏夹、未分组节点
        
        # 默认不包含资产
        with_assets = False
        # 默认不展开特殊节点
        expand_level = 0
        if self.render_tree_type.is_asset_tree:
            with_assets = True
            if search_asset:
                # 资产树中，搜索资产时，展开一级
                expand_level = 1

        f_node, f_assets = self.get_favorite_node(
            search_asset=search_asset, search_node=search_node, 
            asset_category=asset_category, asset_type=asset_type, 
            with_assets=with_assets
        )
        u_node, u_assets = self.get_ungrouped_node_if_need(
            search_asset=search_asset, search_node=search_node, 
            asset_category=asset_category, asset_type=asset_type, 
            with_assets=with_assets
        )

        nodes = [n for n in [f_node, u_node] if n]
        if not nodes:
            return []
        
        serialized_nodes = self.serialize_nodes(
            nodes, tree_type=self.render_tree_type,
            with_asset_amount=with_asset_amount, expand_level=expand_level,
        )
        
        if with_assets:
            assets = [*f_assets, *u_assets]
            serialized_assets = self.serialize_assets(assets)
        else:
            serialized_assets = []

        data = serialized_nodes + serialized_assets
        return data

    @timeit
    def get_favorite_node(self, search_asset=None, search_node=None, asset_category=None, 
                          asset_type=None, with_assets=False):

        assets = UserPermedAssetUtil.get_favorite_assets(
            user=self.tree_user, 
            search_asset=search_asset,
            asset_category=asset_category, 
            asset_type=asset_type
        )
        assets_amount = assets.count()
        node = UserPermAssetTreeNode.favorite(
            assets_amount=assets_amount, 
            assets_amount_total=assets_amount
        )

        if search_node and not node.match(search_node):
            return None, []

        if not with_assets:
            return node, []
        
        if assets_amount == 0:
            return node, []

        assets_attrs = list(assets.values(*AssetTreeNodeAsset.model_values))
        assets = node.init_assets(assets_attrs)
        return node, assets

    @timeit
    def get_ungrouped_node_if_need(self, search_asset=None, search_node=None, 
                                   asset_category=None, asset_type=None, with_assets=False):

        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            # 未分组节点功能关闭
            return None, []

        if self.org_is_global:
            # 全局组织不返回未分组节点
            return None, []

        org = self.get_tree_user_orgs().first()
        util = UserPermedAssetUtil(user=self.user, org=org)
        assets = util.get_ungrouped_assets(
            search_asset=search_asset, 
            asset_category=asset_category, 
            asset_type=asset_type
        )
        assets_amount = assets.count()
        node = UserPermAssetTreeNode.ungrouped(
            assets_amount=assets_amount, 
            assets_amount_total=assets_amount
        )
        if search_node and not node.match(search_node):
            return None, []
        
        if assets_amount == 0:
            return node, []

        if not with_assets:
            return node, []

        assets_attrs = list(assets.values(*AssetTreeNodeAsset.model_values))
        assets = node.init_assets(assets_attrs)
        return node, assets
