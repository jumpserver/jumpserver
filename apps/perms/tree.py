from django.db.models import Q
from assets.tree.node_tree import AssetNodeTree
from assets.tree.type_tree import AssetTypeTree
from assets.models import Asset
from perms.utils.user_perm_asset import UserPermAssetUtil
from common.utils import lazyproperty

__all__ = ['UserAssetNodeTree', 'UserAssetTypeTree']


class UserAssetNodeTree(AssetNodeTree):

    def __init__(self, user, org=None):
        super().__init__(org=org)
        self.util = UserPermAssetUtil(user=user, org=org)
        self.cache_key_scope_assets_ids = 'cache_key_org_{}_user_{}_scope_assets_ids'.format(
            str(self.org.id), str(self.util._user.id)
        )
    
    def _scope_assets_ids(self):
        return self.util.user_permed_all_assets_ids


class UserAssetTypeTree(AssetTypeTree):

    def __init__(self, user, org=None):
        self.util = UserPermAssetUtil(user=user, org=org)
        super().__init__(org=org)
    
    @lazyproperty
    def scope_assets_queryset(self):
        assets =self.util.user_permed_all_assets()
        return assets
