import copy
from collections import defaultdict
from assets.api.xtree import AssetNodeTreeApi, AssetGenericTreeApi, AssetTypeTreeApi
from .mixin import SelfOrPKUserMixin
from orgs.utils import current_org
from perms.tree import UserAssetNodeTree, UserAssetTypeTree

__all__ = [
    'UserAssetNodeTreeApi', 'UserAssetTypeTreeApi', 
    'UserAssetNodeTreeSyncApi', 'UserAssetTypeTreeSyncApi'
]


class UserAssetGenericTreeApi(SelfOrPKUserMixin, AssetGenericTreeApi):
    with_assets_amount = True

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


class UserAssetGenericTreeSyncApi(UserAssetGenericTreeApi):
    sync = True
    page_limit = 10000
    offset = 0

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        offset = request.query_params.get('offset')
        if isinstance(offset, str) and offset.isdigit():
            self.offset = int(offset)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.headers['X-JMS-TREE-OFFSET'] = self.offset
        return response

    def get_tree_data(self, tree):
        tree: UserAssetNodeTree
        if self.offset == 0:
            data_nodes = self.get_tree_data_nodes(tree)
        else:
            data_nodes = []
        data_assets_offset = self.get_tree_data_assets_offset(
            tree, offset=self.offset, page_limit=self.page_limit
        )
        self.offset += self.page_limit
        data = list(data_nodes) + list(data_assets_offset)
        return data
    
    def get_tree_data_nodes(self, tree):
        tree: UserAssetNodeTree
        tree_nodes = tree.get_nodes()
        extra_nodes = getattr(tree, 'get_extra_nodes', lambda: [])()
        for n in extra_nodes:
            setattr(n, 'open', False)
        nodes = extra_nodes + tree_nodes
        data_nodes = self.serialize_nodes(nodes, with_asset_amount=self.with_assets_amount)
        self.offset = 0
        return data_nodes
    
    def get_tree_data_assets_offset(self, tree, offset, page_limit):
        assets = tree.filter_assets()
        assets = assets[offset:(offset + page_limit)]
        serialized_assets = self.serialize_assets_with_parent(tree, assets)
        data_assets_offset = serialized_assets
        return data_assets_offset
    
    def serialize_assets_with_parent(self, tree, assets):
        raise NotImplementedError()


class UserAssetNodeTreeSyncApi(UserAssetGenericTreeSyncApi, UserAssetNodeTreeApi):
    
    def serialize_assets_with_parent(self, tree, assets):
        tree: UserAssetNodeTree
        aid_key_mapper = defaultdict(set)
        for tn in tree.get_nodes():
            for aid in tn.assets_ids:
                aid_key_mapper[aid].add(tn.key)
        f_aids = tree.favorite_assets_ids
        for aid in f_aids:
            aid = str(aid).replace('-', '')
            aid_key_mapper[aid].add(tree.SpecialKey.FAVORITE)
        u_aids = tree.ungrouped_assets_ids
        for aid in u_aids:
            aid = str(aid).replace('-', '')
            aid_key_mapper[aid].add(tree.SpecialKey.UNGROUPED)
        
        def get_parent_keys(asset, platform):
            aid = str(asset.id).replace('-', '')
            return aid_key_mapper[aid]
        
        serialized_assets = self.serialize_assets(assets, get_pid=get_parent_keys)
        return serialized_assets
    

class UserAssetTypeTreeApi(UserAssetGenericTreeApi, AssetTypeTreeApi):

    def get_asset_tree(self, org):
        tree = UserAssetTypeTree(user=self.tree_user, org=org)
        tree.init()
        return tree
    

class UserAssetTypeTreeSyncApi(UserAssetGenericTreeSyncApi, UserAssetTypeTreeApi):

    def serialize_assets_with_parent(self, tree, assets):
        tree: UserAssetTypeTree

        def get_parent_key(asset, platform):
            parent = tree.get_node(str(asset.platform_id))
            return parent.id if parent else ''

        serialized_assets = self.serialize_assets(assets, get_pid=get_parent_key)
        return serialized_assets
    