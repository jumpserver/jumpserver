from assets.api.xtree import AssetNodeTreeApi, AssetGenericTreeApi, AssetTypeTreeApi
from .mixin import SelfOrPKUserMixin
from orgs.utils import current_org
from perms.tree import UserAssetNodeTree, UserAssetTypeTree

__all__ = ['UserAssetNodeTreeApi', 'UserAssetTypeTreeApi']


class UserAssetGenericTreeApi(SelfOrPKUserMixin, AssetGenericTreeApi):

    @property
    def tree_user(self):
        return self.user
    
    @property
    def tree_orgs(self):
        if current_org.is_root():
            orgs = self.tree_user.orgs.all()
        else:
            orgs = self.tree_user.orgs.filter(id=current_org.id)
        return orgs


class UserAssetNodeTreeApi(UserAssetGenericTreeApi, AssetNodeTreeApi):
    
    def get_asset_tree(self, org):
        tree = UserAssetNodeTree(user=self.tree_user, org=org)
        tree.init()
        return tree


class UserAssetTypeTreeApi(UserAssetGenericTreeApi, AssetTypeTreeApi):

    def get_asset_tree(self, org):
        tree = UserAssetTypeTree(user=self.tree_user, org=org)
        tree.init()
        return tree