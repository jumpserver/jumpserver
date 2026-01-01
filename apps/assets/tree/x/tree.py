from django.db.models import QuerySet
from assets.models import Asset, Node, Platform, Zone
from labels.models import Label
from .tree_node import NodeAssetTreeNode


class Tree:

    def __init__(self):
        self.root = None
        self.tree_nodes = {}


class AssetsTreeMixin:

    asset_filter_fields = [ 'id', 'node_id', 'platform_id', 'zone_id', 'is_active', 'org_id' ]
    asset_search_fields = [ 'name__icontains', 'address__icontains' ]

    def __init__(self):
        super().__init__()
        self.assets_queryset = None
        self.tree_nodes_assets_amount_mapper = {}
        self.tree_nodes_assets_mapper = []

class UsersTreeMixin:

    user_filter_fields = [ 'id', 'user', 'username', 'is_active'  ]
    user_search_fields = [ 'username__icontains', 'email__icontains' ]

    def __init__(self):
        super().__init__()
        self.users_queryset = None
        self.tree_nodes_users_amount_mapper = {}
        self.tree_nodes_users_mapper = []


class NodeAssetTree(Tree, AssetsTreeMixin):

    tree_node_class = NodeAssetTreeNode

    node_filter_fields = [ 'id', 'key' ]
    node_search_fields = [ 'value__icontains' ]

    def __init__(self):
        super().__init__()
        self.nodes: QuerySet[Node] = []

class PlatformAssetTree(Tree, AssetsTreeMixin):

    platform_filter_fields = [ 'id', 'category', 'type' ]
    platform_search_fields = [ 'name__icontains', 'category__icontains', 'type__icontains' ]

    def __init__(self):
        super().__init__()
        self.platforms: QuerySet[Platform] = []


# ---

class ZoneAssetTree(Tree, AssetsTreeMixin):

    zone_filter_fields = [ 'id' ]
    zone_search_fields = [ 'name__icontains' ]

    def __init__(self):
        super().__init__()
        self.zones: QuerySet[Zone] = []

class LabelTree(Tree):
    
    label_filter_fields = [ 'id' ]
    label_search_fields = [ 'name__icontains', 'value__icontains' ]

    def __init__(self):
        super().__init__()
        self.labels: QuerySet[Label] = []

class LabelAssetTree(LabelTree, AssetsTreeMixin):
    pass


class LabelUserTree(LabelTree, UsersTreeMixin):
    pass
