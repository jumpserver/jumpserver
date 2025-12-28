from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.conf import settings


from common.utils import get_logger, timeit
from assets.api.tree import AbstractAssetTreeAPI
from assets.tree.asset_tree import AssetTreeNodeAsset
from perms.tree import UserPermAssetTree, UserPermAssetTreeNode
from perms.utils.utils import UserPermUtil

from .mixin import SelfOrPKUserMixin

logger = get_logger(__name__)

__all__ = [
    'UserPermedAssetTreeAPI'
]


class UserPermedAssetTreeAPI(SelfOrPKUserMixin, AbstractAssetTreeAPI):

    def get_tree_user(self):
        return self.user

    def get_org_asset_tree(self, **kwargs) -> UserPermAssetTree:
        return self.get_user_org_asset_tree(**kwargs)

    def get_user_org_asset_tree(self, **kwargs) -> UserPermAssetTree:
        tree = UserPermAssetTree(user=self.user, **kwargs)
        return tree
    
    def _render_asset_tree(self, **kwargs):
        data = super()._render_asset_tree(**kwargs)
        expand_node_key = kwargs.pop('expand_node_key', None)
        if expand_node_key:
            # 特殊节点不需要展开，资产树中特殊节点下的资产已经随着节点一起返回
            return data
        
        special_nodes = self.get_special_nodes(with_assets=True, expand_level=0, **kwargs)
        data = special_nodes + data
        return data
    
    def render_node_tree(self, asset_category, asset_type, with_asset_amount):
        data = super().render_node_tree(asset_category, asset_type, with_asset_amount)
        special_nodes = self.get_special_nodes(
            with_assets=False, expand_level=0, asset_category=asset_category, asset_type=asset_type, 
            with_asset_amount=with_asset_amount
        )
        data = special_nodes + data
        return data
    
    def get_special_nodes(self, search_asset=None, search_node=None, 
                          asset_category=None, asset_type=None,
                          with_assets=False, expand_level=0, with_asset_amount=False):
        f_node, f_assets = self.get_favorite_node(
            search_asset=search_asset, search_node=search_node, 
            asset_category=asset_category, asset_type=asset_type, with_assets=with_assets
        )
        u_node, u_assets = self.get_ungrouped_node_if_need(
            search_asset=search_asset, search_node=search_node, 
            asset_category=asset_category, asset_type=asset_type, with_assets=with_assets
        )

        nodes = []
        if f_node:
            nodes.append(f_node)
        if u_node:
            nodes.append(u_node)

        if not nodes:
            return []
        
        if search_asset:
            expand_level = 1
        
        serialized_nodes = self.serialize_nodes(
            nodes, tree_type=self.render_tree_type,
            with_asset_amount=with_asset_amount, expand_level=expand_level,
        )
        if with_assets:
            assets = f_assets + u_assets
            serialized_assets = self.serialize_assets(assets)
        else:
            serialized_assets = []
        
        data = serialized_nodes + serialized_assets
        return data

    def get_favorite_node(self, search_asset=None, search_node=None, asset_category=None, 
                          asset_type=None, with_assets=False):
        assets = UserPermUtil.get_favorite_assets(
            user=self.user, search_asset=search_asset,
            asset_category=asset_category, asset_type=asset_type
        )
        assets_amount = assets.count()
        f_node = UserPermAssetTreeNode.favorite(
            assets_amount=assets_amount, assets_amount_total=assets_amount
        )
        if not f_node.match(search_node):
            return None, []
        
        if assets_amount == 0:
            return f_node, []

        if with_assets:
            assets_attrs = list(assets.values(*AssetTreeNodeAsset.model_values))
            assets = f_node.init_assets(assets_attrs)
        else:
            assets = []
        return f_node, assets

    def get_ungrouped_node_if_need(self, search_asset=None, search_node=None, asset_category=None, 
                                   asset_type=None, with_assets=False):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return None, []
        if self.org_is_global:
            # 全局组织不返回未分组节点
            return None, []
        org = self.get_tree_user_orgs().first()
        util = UserPermUtil(user=self.user, org=org)
        assets = util.get_ungrouped_assets(
            search_asset=search_asset, 
            asset_category=asset_category, asset_type=asset_type
        )
        assets_amount = assets.count()
        u_node = UserPermAssetTreeNode.ungrouped(
            assets_amount=assets_amount, assets_amount_total=assets_amount
        )
        if not u_node.match(search_node):
            return None, []
        
        if assets_amount == 0:
            return u_node, []

        if with_assets:
            assets_attrs = list(assets.values(*AssetTreeNodeAsset.model_values))
            assets = u_node.init_assets(assets_attrs)
        else:
            assets = []
        return u_node, assets
