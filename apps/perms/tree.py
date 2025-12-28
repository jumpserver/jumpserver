from django.utils.translation import gettext_lazy as _
from collections import defaultdict
from django.db.models import Q, Count, TextChoices
from django.core.cache import cache

from common.utils import get_logger
from users.models import User
from assets.models import FavoriteAsset, Asset
from assets.tree.asset_tree import AssetTree, AssetTreeNode, AssetTreeNodeAsset
from perms.utils.utils import UserPermedAssetUtil


__all__ = ['UserPermAssetTree']


logger = get_logger(__name__)


class UserPermAssetTreeNode(AssetTreeNode):

    class Type(TextChoices):
        DN = 'direct_node', 'Direct Node'
        DA = 'direct_asset', 'Direct Asset'
        BRIDGE = 'bridge', 'Bridge'

    class SpecialKey(TextChoices):
        FAVORITE = 'favorite', _('Favorite')
        UNGROUPED = 'ungrouped', _('Ungrouped')
    
    def __init__(self, tp, **kwargs):
        self.tp = tp
        super().__init__(**kwargs)
    
    @classmethod
    def favorite(cls, **kwargs):
        node = cls(
            tp=cls.Type.BRIDGE,
            _id=cls.SpecialKey.FAVORITE.value,
            key=cls.SpecialKey.FAVORITE.value,
            value=cls.SpecialKey.FAVORITE.label,
            **kwargs
        )
        return node
    
    @classmethod
    def ungrouped(cls, **kwargs):
        node = cls(
            tp=cls.Type.BRIDGE,
            _id=cls.SpecialKey.UNGROUPED.value,
            key=cls.SpecialKey.UNGROUPED.value,
            value=cls.SpecialKey.UNGROUPED.label,
            **kwargs
        )
        return node
    
    def as_dict(self, simple=True):
        data = super().as_dict(simple)
        data.update({
            'type': self.tp,
        })
        return data

    

class UserPermAssetTree(AssetTree):

    TreeNode = UserPermAssetTreeNode

    def __init__(self, user, **kwargs):

        self._user: User = user
        self._util = UserPermedAssetUtil(user, org=kwargs.get('org'))
        kwargs.update({
            # 用户授权树只返回有资产的节点
            'full_tree': False,
        })
        super().__init__(**kwargs)

    def _make_assets_q_object(self):
        q = super()._make_assets_q_object()
        q_perm_assets = Q(id__in=list(self._util._user_direct_asset_ids))
        q_perm_nodes = Q(node_id__in=list(self._util._user_direct_node_all_children_ids))
        q = q & (q_perm_assets | q_perm_nodes)
        return q

    def _get_tree_node_data(self, node_id):
        data = super()._get_tree_node_data(node_id)
        if node_id in self._util._user_direct_node_all_children_ids:
            tp = UserPermAssetTreeNode.Type.DN
        elif self._nodes_assets_amount_mapper.get(node_id, 0) > 0:
            tp = UserPermAssetTreeNode.Type.DA
        else:
            tp = UserPermAssetTreeNode.Type.BRIDGE
        data.update({ 'tp': tp })
        return data
    
    def print(self, simple=True, count=10):
        self._util.print()
        super().print(simple=simple, count=count)
