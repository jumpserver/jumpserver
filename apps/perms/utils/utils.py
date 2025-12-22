
from common.utils import timeit, lazyproperty, get_logger
from orgs.utils import current_org
from users.models import User
from assets.models import Node
from perms.models import AssetPermission


logger = get_logger(__name__)


__all__ = ['UserPermUtil']


class UserPermUtil(object):

    UserGroupThrough = User.groups.through
    PermUserThrough = AssetPermission.users.through
    PermUserGroupThrough = AssetPermission.user_groups.through
    PermAssetThrough = AssetPermission.assets.through
    PermNodeThrough = AssetPermission.nodes.through

    def __init__(self, user, org=None):
        self._user: User = user
        self._org = org or current_org
        self._user_permission_ids = set()
        self._user_group_ids = set()
        self._user_group_permission_ids = set()
        self._user_direct_asset_ids = set()
        self._user_direct_node_ids = set()
        self._user_direct_node_all_children_ids = set()

    def init(self):
        self._load_user_permission_ids()
        self._load_user_group_ids()
        self._load_user_group_permission_ids()
        self._load_user_direct_asset_ids()
        self._load_user_direct_node_ids()
        self._load_user_direct_node_all_children_ids()
    
    @lazyproperty
    def _user_all_permission_ids(self):
        return self._user_permission_ids | self._user_group_permission_ids

    @timeit
    def _load_user_permission_ids(self):
        perm_ids = self.PermUserThrough.objects.filter(
            user_id=self._user.id
        ).distinct('assetpermission_id').values_list('assetpermission_id', flat=True)
        perm_ids = self._uuids_to_string(perm_ids)
        self._user_permission_ids.update(perm_ids)

    @timeit
    def _load_user_group_ids(self):
        group_ids = self.UserGroupThrough.objects.filter(
            user_id=self._user.id
        ).distinct('usergroup_id').values_list('usergroup_id', flat=True)
        group_ids = self._uuids_to_string(group_ids)
        self._user_group_ids.update(group_ids)
    
    @timeit
    def _load_user_group_permission_ids(self):
        perm_ids = self.PermUserGroupThrough.objects.filter(
            usergroup_id__in=self._user_group_ids
        ).distinct('assetpermission_id').values_list('assetpermission_id', flat=True)
        perm_ids = self._uuids_to_string(perm_ids)
        self._user_group_permission_ids.update(perm_ids)

    @timeit
    def _load_user_direct_asset_ids(self):
        asset_ids = self.PermAssetThrough.objects.filter(
            assetpermission_id__in=self._user_all_permission_ids
        ).distinct('asset_id').values_list('asset_id', flat=True)
        asset_ids = self._uuids_to_string(asset_ids)
        self._user_direct_asset_ids.update(asset_ids)

    @timeit
    def _load_user_direct_node_ids(self):
        node_ids = self.PermNodeThrough.objects.filter(
            assetpermission_id__in=self._user_all_permission_ids
        ).distinct('node_id').values_list('node_id', flat=True)
        node_ids = self._uuids_to_string(node_ids)
        self._user_direct_node_ids.update(node_ids)
    
    @timeit
    def _load_user_direct_node_all_children_ids(self):
        nid_key_pairs = Node.objects.filter(org_id=self._org.id).values_list('id', 'key')
        nid_key_mapper = { str(nid): key for nid, key in nid_key_pairs }

        dn_keys = [ nid_key_mapper[nid] for nid in self._user_direct_node_ids ]

        def has_ancestor_in_direct_nodes(key: str) -> bool:
            ancestor_keys = [ ':'.join(key.split(':')[:i]) for i in range(1, key.count(':') + 1) ]
            return bool(set(ancestor_keys) & set(dn_keys))

        dn_children_ids = [ nid for nid, key in nid_key_mapper.items() if has_ancestor_in_direct_nodes(key) ]

        self._user_direct_node_all_children_ids.update(self._user_direct_node_ids)
        self._user_direct_node_all_children_ids.update(dn_children_ids)
    
    def _uuids_to_string(self, uuids):
        return [ str(u) for u in uuids ]

    def print(self):
        print('user_perm_tree:', self._user.username)
        print('user_permission_ids_count:', len(self._user_permission_ids))
        print('user_group_ids_count:', len(self._user_group_ids))
        print('user_group_permission_ids_count:', len(self._user_permission_ids) - len(self._user_group_ids))
        print('user_all_permission_ids_count:', len(self._user_all_permission_ids))
        print('user_direct_asset_ids_count:', len(self._user_direct_asset_ids))
        print('user_direct_node_ids_count:', len(self._user_direct_node_ids))
        print('user_direct_node_all_children_ids_count:', len(self._user_direct_node_all_children_ids))
