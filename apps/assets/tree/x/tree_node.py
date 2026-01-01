
class TreeNode:
    def __init__(self):
        self.key = None
        self.name = None
        self.parent = None
        self.children = []


class AssetsMixin:
    fetch_asset_fields = [
        'id', 'name', 'address', 'node_id',
        'platform_id', 'platform__category', 'platform__type',
        'is_active', 'comment', 'zone_id', 'org_id', 
    ]

    def __init__(self):
        self.assets_amount = 0
        self.assets_amount_total = 0
        self.assets = []


class UsersMixin:

    def __init__(self):
        self.users_amount = 0
        self.users_amount_total = 0
        self.users = []


class NodeAssetTreeNode(TreeNode, AssetsMixin):
    def __init__(self):
        super().__init__()
        self.node = None


class PlatformAssetTreeNode(TreeNode, AssetsMixin):

    def __init__(self):
        super().__init__()
        self.type = 'category | type | platform'
        self.platform_category = None
        self.platform_type = None
        self.platform = None

# ---


class ZoneAssetTreeNode(TreeNode, AssetsMixin):

    def __init__(self):
        super().__init__()
        self.zone = None


class LabelTreeNode(TreeNode):

    def __init__(self):
        super().__init__()
        self.label = None

    
class LabelAssetTreeNode(LabelTreeNode, AssetsMixin):
    pass


class LabelUserTreeNode(LabelTreeNode, UsersMixin):
    pass
