
from django.db.models import Q

from common.utils import timeit, lazyproperty, get_logger, is_uuid
from orgs.utils import current_org, tmp_to_org
from users.models import User
from assets.models import Node, Asset, FavoriteAsset
from perms.models import AssetPermission


logger = get_logger(__name__)


__all__ = ['UserPermedAssetUtil']


class UserPermedAssetUtil(object):

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
        self._user_all_permission_ids = set()
        self._user_direct_asset_ids = set()
        self._user_direct_node_ids = set()
        self._user_direct_node_all_children_ids = set()
        self._init()

    @timeit
    def _init(self):
        self._load_user_permission_ids()
        self._load_user_group_ids()
        self._load_user_group_permission_ids()
        self._load_user_direct_asset_ids()
        self._load_user_direct_node_ids()
        self._load_user_direct_node_all_children_ids()

    @timeit
    def _load_user_permission_ids(self):
        perm_ids = self.PermUserThrough.objects.filter(
            user_id=self._user.id, 
            assetpermission__org_id=self._org.id
        ).distinct('assetpermission_id').values_list('assetpermission_id', flat=True)
        perm_ids = self._uuids_to_string(perm_ids)
        self._user_permission_ids.update(perm_ids)
        self._user_all_permission_ids.update(perm_ids)

    @timeit
    def _load_user_group_ids(self):
        group_ids = self.UserGroupThrough.objects.filter(
            user_id=self._user.id,
            usergroup__org_id=self._org.id
        ).distinct('usergroup_id').values_list('usergroup_id', flat=True)
        group_ids = self._uuids_to_string(group_ids)
        self._user_group_ids.update(group_ids)
    
    @timeit
    def _load_user_group_permission_ids(self):
        perm_ids = self.PermUserGroupThrough.objects.filter(
            usergroup_id__in=self._user_group_ids,
            assetpermission__org_id=self._org.id
        ).distinct('assetpermission_id').values_list('assetpermission_id', flat=True)
        perm_ids = self._uuids_to_string(perm_ids)
        self._user_group_permission_ids.update(perm_ids)
        self._user_all_permission_ids.update(perm_ids)

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

        dn_keys = [ 
            nid_key_mapper[nid] for nid in self._user_direct_node_ids 
        ]

        def has_ancestor_in_direct_nodes(key: str) -> bool:
            ancestor_keys = [ 
                ':'.join(key.split(':')[:i]) 
                for i in range(1, key.count(':') + 1) 
            ]
            return bool(set(ancestor_keys) & set(dn_keys))

        dn_children_ids = [ 
            nid for nid, key in nid_key_mapper.items() 
            if has_ancestor_in_direct_nodes(key) 
        ]

        self._user_direct_node_all_children_ids.update(self._user_direct_node_ids)
        self._user_direct_node_all_children_ids.update(dn_children_ids)
    
    def get_node_assets(self, node: Node):
        ''' 获取节点下授权的直接资产 '''
        q = Q(node_id=node.id)
        if str(node.id) not in self._user_direct_node_all_children_ids:
            q &= Q(id__in=self._user_direct_asset_ids)
        assets = Asset.objects.filter(org_id=self._org.id).filter(q)
        return assets

    def get_node_all_assets(self, node: Node):
        ''' 获取节点及其子节点下所有授权资产 '''
        if str(node.id) in self._user_direct_node_all_children_ids:
            assets = node.get_all_assets()
            return assets
        
        children_ids = node.get_all_children(with_self=True).values_list('id', flat=True)
        children_ids = self._uuids_to_string(children_ids)
        dn_all_nodes_ids = set(children_ids) & self._user_direct_node_all_children_ids
        other_nodes_ids = set(children_ids) - dn_all_nodes_ids

        q = Q(node_id__in=dn_all_nodes_ids)
        q |= Q(node_id__in=other_nodes_ids) & Q(id__in=self._user_direct_asset_ids)
        assets = Asset.objects.filter(org_id=self._org.id).filter(q).valid()
        return assets
    
    def get_all_assets_of_org(self):
        with tmp_to_org(self._org):
            root_node = Node.org_root()
            assets = self.get_node_all_assets(root_node)
            return assets
    
    @classmethod
    def get_all_assets(cls, user):
        if current_org.is_root():
            orgs = user.orgs.all()
        else:
            orgs = user.orgs.filter(id=current_org.id)
        
        assets = Asset.objects.none()
        for org in orgs:
            _util = cls(user=user, org=org)
            org_assets = _util.get_all_assets_of_org()
            assets |= org_assets
        return assets

    @classmethod
    def get_favorite_assets(cls, user, search_asset=None, asset_category=None, asset_type=None):
        asset_ids = FavoriteAsset.get_user_favorite_asset_ids(user)
        assets = cls.filter_assets(
            asset_ids=asset_ids,
            search_asset=search_asset, 
            asset_category=asset_category, 
            asset_type=asset_type,
        )
        return assets
    
    def get_ungrouped_assets(self, search_asset=None, asset_category=None, asset_type=None):
        asset_ids = self._user_direct_asset_ids
        assets = self.filter_assets(
            asset_ids=asset_ids, 
            search_asset=search_asset, 
            asset_category=asset_category, 
            asset_type=asset_type,
        )
        return assets
    
    @classmethod
    def filter_assets(cls, asset_ids, search_asset=None, asset_category=None, asset_type=None):
        q = cls._make_assets_q_object(
            asset_ids=asset_ids,
            search_asset=search_asset, 
            asset_category=asset_category, 
            asset_type=asset_type
            )
        assets = Asset.objects.filter(q).valid()
        return assets
    
    @staticmethod
    def _make_assets_q_object(asset_ids=None, search_asset=None, asset_category=None, 
                              asset_type=None):
        q = Q()
        if asset_ids:
            q &= Q(id__in=asset_ids)
        if search_asset:
            q &= Q(name__icontains=search_asset) | Q(address__icontains=search_asset)
        if asset_category:
            q &= Q(platform__category=asset_category)
        if asset_type:
            q &= Q(platform__type=asset_type)
        return q
    
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
