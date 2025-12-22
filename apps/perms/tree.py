from django.db.models import Q

from common.utils import timeit, get_logger
from users.models import User
from assets.tree.asset_tree import AssetSearchTree, AssetTreeNode
from perms.utils.utils import UserPermUtil


__all__ = ['UserPermTree']


logger = get_logger(__name__)


class PermTreeNode(AssetTreeNode):

    class Type:
        BRIDGE = 'bridge' # Not a perm node and not has direct perm asset node
        DN = 'dn' # Direct perm node
        DA = 'da' # Has direct perm asset node

    def __init__(self, tp, _id, key, value, assets_count=0):
        super().__init__(_id, key, value, assets_count)
        self.type = tp or self.Type.BRIDGE
    
    def as_dict(self, simple=True):
        base_dict = super().as_dict(simple=simple)
        base_dict.update({
            'type': self.type,
        })
        return base_dict


class UserPermTree(AssetSearchTree):

    TreeNode = PermTreeNode


    def __init__(self, user=None, assets_q_object=None, category=None, org=None):
        super().__init__(assets_q_object=assets_q_object, category=category, org=org)
        self._user: User = user
        self._util = UserPermUtil(user, org=self._org)

    def _make_assets_q_object(self):
        q_base = super()._make_assets_q_object()
        q_perm_assets = Q(id__in=self._util._user_direct_asset_ids)
        q_perm_nodes = Q(node_id__in=self._util._user_direct_node_all_children_ids)
        q = q_base & (q_perm_assets | q_perm_nodes)
        return q

    def _get_tree_node_data(self, node_id):
        data = super()._get_tree_node_data(node_id)
        if node_id in self._util._user_direct_node_all_children_ids:
            tp = PermTreeNode.Type.DN
        elif self._nodes_assets_count_mapper.get(node_id, 0) > 0:
            tp = PermTreeNode.Type.DA
        else:
            tp = PermTreeNode.Type.BRIDGE
        data.update({
            'tp': tp,
        })
        return data

    def print(self, simple=True, count=10):
        self._util.print()
        super().print(simple=simple, count=count)
