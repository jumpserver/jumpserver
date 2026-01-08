
from django.db.models import Q

from common.utils import timeit, get_logger, lazyproperty
from orgs.utils import current_org, tmp_to_org
from users.models import User
from assets.models import Node, Asset, FavoriteAsset
from perms.models import AssetPermission


logger = get_logger(__name__)


__all__ = ['UserPermAssetUtil']


class UserPermAssetUtil:

    AssetNodeThrough = Asset.nodes.through
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
        self._init()
    
    @timeit
    def _init(self):
        self._load_user_permission_ids()
        self._load_user_group_ids()
        self._load_user_group_permission_ids()
        self._load_user_direct_asset_ids()
        self._load_user_direct_node_ids()

    @timeit
    def _load_user_permission_ids(self):
        perm_ids = self.PermUserThrough.objects.filter(user_id=self._user.id).values_list(
            'assetpermission_id', flat=True
        )
        self._user_permission_ids.update(perm_ids)

    @timeit
    def _load_user_group_ids(self):
        group_ids = self.UserGroupThrough.objects.filter(user_id=self._user.id).values_list(
            'usergroup_id', flat=True
        )
        self._user_group_ids.update(group_ids)
    
    @timeit
    def _load_user_group_permission_ids(self):
        perm_ids = self.PermUserGroupThrough.objects.filter(
            usergroup_id__in=self._user_group_ids
        ).values_list('assetpermission_id', flat=True)
        self._user_group_permission_ids.update(perm_ids)
    
    @lazyproperty
    def user_all_permission_ids(self):
        ids = self._user_permission_ids | self._user_group_permission_ids
        ids = AssetPermission.objects.filter(id__in=ids, org_id=self._org.id).values_list(
            'id', flat=True
        )
        return ids

    @timeit
    def _load_user_direct_asset_ids(self):
        asset_ids = self.PermAssetThrough.objects.filter(
            assetpermission_id__in=self.user_all_permission_ids
        ).distinct('asset_id').values_list('asset_id', flat=True)
        self._user_direct_asset_ids.update(asset_ids)

    @timeit
    def _load_user_direct_node_ids(self):
        node_ids = self.PermNodeThrough.objects.filter(
            assetpermission_id__in=self.user_all_permission_ids
        ).distinct('node_id').values_list('node_id', flat=True)
        self._user_direct_node_ids.update(node_ids)
    
    @lazyproperty
    def user_all_permed_nodes_ids(self):
        dn_ids = self._user_direct_node_ids
        dn_objs = Node.objects.filter(id__in=dn_ids, org_id=self._org.id).only('key')
        all_permed_nodes_ids = Node.get_nodes_all_children(dn_objs, with_self=True).values_list('id', flat=True)
        return set(all_permed_nodes_ids)
    
    @lazyproperty
    def user_all_permed_nodes_assets_ids(self):
        from assets.tree.node_tree import relation
        all_permed_nodes_aids = set()
        for nid in self.user_all_permed_nodes_ids:
            aids = relation.nid_aids_mapper.get(str(nid), [])
            all_permed_nodes_aids.update(aids)
        return all_permed_nodes_aids
    
    @lazyproperty
    def only_direct_assets_ids(self):
        # 目的就是查询用户授权的所有资产时 id__in 的数量尽可能少
        aids = set(self._user_direct_asset_ids) - set(self.user_all_permed_nodes_assets_ids)
        return aids

    @lazyproperty
    def user_permed_all_assets_ids(self):
        q = Q(asset_id__in=self.only_direct_assets_ids) | Q(node_id__in=self.user_all_permed_nodes_ids)
        aids = self.AssetNodeThrough.objects.filter(q).values_list('asset_id', flat=True).distinct()
        return set(aids)

    def user_permed_all_assets(self):
        q = Q(org_id=self._org.id)
        q &= Q(id__in=self.only_direct_assets_ids) | Q(nodes__id__in=self.user_all_permed_nodes_ids)
        assets = Asset.objects.filter(q).distinct()
        return assets
    
