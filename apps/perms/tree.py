from django.utils.translation import gettext_lazy as _
from django.db.models import Q, TextChoices
from assets.tree.node_tree import AssetNodeTree
from assets.tree.type_tree import AssetTypeTree
from assets.models import Asset, FavoriteAsset
from perms.utils.user_perm_asset import UserPermAssetUtil
from common.utils import lazyproperty

__all__ = ['UserAssetNodeTree', 'UserAssetTypeTree']


class UserAssetNodeTree(AssetNodeTree):

    class SpecialKey(TextChoices):
        FAVORITE = 'favorite', _('Favorite')
        UNGROUPED = 'ungrouped', _('Ungrouped')

    def __init__(self, user, org=None):
        super().__init__(org=org)
        self.user = user
        self.org = org
        self.util = UserPermAssetUtil(user=user, org=org)
        self.cache_key_scope_assets_ids = 'cache_key_org_{}_user_{}_scope_assets_ids'.format(
            str(self.org.id), str(self.util._user.id)
        )
    
    def _scope_assets_ids(self):
        return self.util.user_permed_all_assets_ids

    def get_node(self, key):
        node = super().get_node(key)
        if node:
            return node
        if key == self.SpecialKey.FAVORITE:
            return self.favorite_tree_node
        if key == self.SpecialKey.UNGROUPED:
            return self.ungrouped_tree_node
    
    def get_extra_nodes(self):
        f_tree_node = self.create_favorite_tree_node()
        u_tree_node = self.create_ungrouped_tree_node()
        return [f_tree_node, u_tree_node]
    
    def create_favorite_tree_node(self):
        self.favorite_tree_node.assets_amount_total = self.favorite_assets_ids.count()
        return self.favorite_tree_node

    @lazyproperty
    def favorite_tree_node(self):
        kwargs = {
            'raw_id': self.SpecialKey.FAVORITE,
            'key': self.SpecialKey.FAVORITE,
            'name': self.SpecialKey.FAVORITE.label,
            'parent_key': None
        }
        tree_node = self.create_tree_node(**kwargs)
        return tree_node

    def create_ungrouped_tree_node(self):
        self.ungrouped_tree_node.assets_amount_total = len(self.ungrouped_assets_ids)
        return self.ungrouped_tree_node

    @lazyproperty
    def ungrouped_tree_node(self):
        kwargs = {
            'raw_id': self.SpecialKey.UNGROUPED,
            'key': self.SpecialKey.UNGROUPED,
            'name': self.SpecialKey.UNGROUPED.label,
            'parent_key': None
        }
        tree_node = self.create_tree_node(**kwargs)
        return tree_node
    
    def _filter_node_assets(self, node_key):
        if node_key == self.SpecialKey.FAVORITE:
            return self.filter_favorite_assets()
        if node_key == self.SpecialKey.UNGROUPED:
            return self.filter_ungrouped_assets()
        return super()._filter_node_assets(node_key)
    
    @property
    def ungrouped_assets_ids(self):
        return self.util._user_direct_asset_ids

    @property
    def favorite_assets_ids(self):
        return FavoriteAsset.get_user_favorite_asset_ids(user=self.user)

    def filter_favorite_assets(self):
        return Asset.objects.filter(id__in=self.favorite_assets_ids)

    def filter_ungrouped_assets(self):
        return Asset.objects.filter(id__in=self.util._user_direct_asset_ids)


class UserAssetTypeTree(AssetTypeTree):

    def __init__(self, user, org=None):
        super().__init__(org=org)
        self.user = user
        self.util = UserPermAssetUtil(user=user, org=org)
        self.cache_key_platform_assets_amount_mapper = f'''
            cache_key_user_{str(self.user.id)}_org_{str(self.org.id)}_platform_assets_amount_mapper 
        '''
    
    @lazyproperty
    def scope_assets_queryset(self):
        assets = self.util.user_permed_all_assets()
        return assets
