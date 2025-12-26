from django.utils.translation import gettext_lazy as _
from collections import defaultdict
from django.db.models import Q, Count, TextChoices
from django.core.cache import cache

from common.utils import get_logger
from users.models import User
from assets.models import FavoriteAsset, Asset
from assets.tree.asset_tree import AssetTree, AssetTreeNode, AssetTreeNodeAsset
from perms.utils.utils import UserPermUtil


__all__ = ['UserPermTree']


logger = get_logger(__name__)


class PermTreeNode(AssetTreeNode):

    class Type:
        # Neither a permission node nor a node with direct permission assets
        BRIDGE = 'bridge'
        # Node with direct permission
        DN = 'dn'
        # Node with only direct permission assets
        DA = 'da'

    def __init__(self, tp=None, **kwargs):
        self.type = tp or self.Type.BRIDGE
        super().__init__(**kwargs)
    
    def as_dict(self, simple=True):
        data = super().as_dict(simple=simple)
        data.update({
            'type': self.type,
        })
        return data
    

class UserPermTree(AssetTree):

    TreeNode = PermTreeNode

    def __init__(self, user, **kwargs):

        self._user: User = user
        self._util = UserPermUtil(user, org=kwargs.get('org'))
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
            tp = PermTreeNode.Type.DN
        elif self._nodes_assets_amount_mapper.get(node_id, 0) > 0:
            tp = PermTreeNode.Type.DA
        else:
            tp = PermTreeNode.Type.BRIDGE
        data.update({ 'tp': tp })
        return data
    
    def print(self, simple=True, count=10):
        self._util.print()
        super().print(simple=simple, count=count)
