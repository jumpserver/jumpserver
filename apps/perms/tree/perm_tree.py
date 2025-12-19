
from django.db.models import Q
from common.utils import timeit, get_logger

from users.models import User, UserGroup
from assets.tree.asset_tree import AssetSearchTree, AssetTreeNode
from perms.models import AssetPermission


__all__ = ['UserPermTree']


logger = get_logger(__name__)


class PermTreeNode(AssetTreeNode):

    class Type:
        BRIDGE = 'bridge' # Not a perm node and not has direct perm asset
        DN = 'dn' # Direct perm node
        DA = 'da' # Has direct perm asset

    def __init__(self, tp, _id, key: str, value: str, assets_count: int=0):
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

    UserGroupThrough = User.groups.through
    PermUserThrough = AssetPermission.users.through
    PermUserGroupThrough = AssetPermission.user_groups.through
    PermAssetThrough = AssetPermission.assets.through
    PermNodeThrough = AssetPermission.nodes.through


    def __init__(self, user=None, assets_q_object=None, category=None, org=None):
        super().__init__(assets_q_object=assets_q_object, category=category, org=org)
        self._user: User = user
        self._user_permission_ids = set()
        self._user_group_ids = set()
        self._user_group_permission_ids = set()
        self._user_all_permission_ids = set()
        self._user_direct_node_ids = set()
        self._user_direct_node_all_children_ids = set()
        self._user_direct_asset_ids = set()

    @timeit
    def _pre_build(self):
        super()._pre_build()
        self._load_user_permission_ids()
        self._load_user_group_permission_ids()
        self._load_user_direct_asset_ids()
        self._load_user_direct_node_ids()

    def _make_assets_q_object(self):
        self._load_user_direct_node_all_children_ids()
        q_base = super()._make_assets_q_object()
        q_perm_assets = Q(id__in=self._user_direct_asset_ids)
        q_perm_nodes = Q(node_id__in=self._user_direct_node_all_children_ids)
        q = q_base & (q_perm_assets | q_perm_nodes)
        return q

    def _get_tree_node_data(self, node_id):
        data = super()._get_tree_node_data(node_id)
        if node_id in self._user_direct_node_all_children_ids:
            tp = PermTreeNode.Type.DN
        elif self._nodes_assets_count_mapper.get(node_id, 0) > 0:
            tp = PermTreeNode.Type.DA
        else:
            tp = PermTreeNode.Type.BRIDGE
        data.update({
            'tp': tp,
        })
        return data

    @timeit
    def _load_user_permission_ids(self):
        perm_ids = self.PermUserThrough.objects.filter(
            user_id=self._user.id
        ).distinct('assetpermission_id').values_list('assetpermission_id', flat=True)
        perm_ids = self._uuids_to_string(perm_ids)
        self._user_permission_ids.update(perm_ids)
        self._user_all_permission_ids.update(perm_ids)
    
    @timeit
    def _load_user_group_permission_ids(self):
        self._load_user_group_ids()
        perm_ids = self.PermUserGroupThrough.objects.filter(
            usergroup_id__in=self._user_group_ids
        ).distinct('assetpermission_id').values_list('assetpermission_id', flat=True)
        perm_ids = self._uuids_to_string(perm_ids)
        self._user_group_permission_ids.update(perm_ids)
        self._user_all_permission_ids.update(perm_ids)
    
    @timeit
    def _load_user_group_ids(self):
        group_ids = self.UserGroupThrough.objects.filter(
            user_id=self._user.id
        ).distinct('usergroup_id').values_list('usergroup_id', flat=True)
        group_ids = self._uuids_to_string(group_ids)
        self._user_group_ids.update(group_ids)
    
    @timeit
    def _load_user_direct_node_ids(self):
        node_ids = self.PermNodeThrough.objects.filter(
            assetpermission_id__in=self._user_all_permission_ids
        ).distinct('node_id').values_list('node_id', flat=True)
        node_ids = self._uuids_to_string(node_ids)
        self._user_direct_node_ids.update(node_ids)
    
    @timeit
    def _load_user_direct_node_all_children_ids(self):
        dn_keys = [ self._nodes_attr_mapper[nid]['key'] for nid in self._user_direct_node_ids ]

        def has_ancestor_in_direct_nodes(key: str) -> bool:
            ancestor_keys = [ 
                ':'.join(key.split(':')[:i]) 
                for i in range(1, key.count(':') + 1) 
            ]
            return bool(set(ancestor_keys) & set(dn_keys))

        _ids = [
            nid for nid, attr in self._nodes_attr_mapper.items() 
            if has_ancestor_in_direct_nodes(attr['key'])
        ]

        self._user_direct_node_all_children_ids.update(self._user_direct_node_ids)
        self._user_direct_node_all_children_ids.update(_ids)

    @timeit
    def _load_user_direct_asset_ids(self):
        asset_ids = self.PermAssetThrough.objects.filter(
            assetpermission_id__in=self._user_all_permission_ids
        ).distinct('asset_id').values_list('asset_id', flat=True)
        asset_ids = self._uuids_to_string(asset_ids)
        self._user_direct_asset_ids.update(asset_ids)

    def print(self, simple=True, count=10):
        print('user_perm_tree:', self._user.username)
        print('user_permission_ids_count:', len(self._user_permission_ids))
        print('user_group_ids_count:', len(self._user_group_ids))
        print('user_group_permission_ids_count:', len(self._user_permission_ids) - len(self._user_group_ids))
        print('user_all_permission_ids_count:', len(self._user_all_permission_ids))
        print('user_direct_asset_ids_count:', len(self._user_direct_asset_ids))
        print('user_direct_node_ids_count:', len(self._user_direct_node_ids))
        print('user_direct_node_all_children_ids_count:', len(self._user_direct_node_all_children_ids))
        super().print(simple=simple, count=count)
