from django.db.models import Q
from orgs.models import Organization
from orgs.utils import current_org
from assets.models import Node, Asset
from django.db.models import Count
from .tree import Tree, TreeNode
from common.utils import lazyproperty

__all__ = ['NodeTreeNode', 'AssetNodeTree', 'TreeAsset']


class NodeTreeNode(TreeNode):
    model_only_fields = ['id', 'key', 'value']

    def __init__(self, id, **kwargs):
        super().__init__(**kwargs)
        self.id = id
        self.value = self.name
        self.assets_amount = 0
        self.assets = []
    
    def set_assets_amount(self, amount):
        self.assets_amount = amount

    @lazyproperty
    def assets_amount_total(self):
        count = self.assets_amount
        for child in self.children:
            child: NodeTreeNode
            count += child.assets_amount_total
        return count


class TreeAsset:
    model_only_fields = [
        'id', 'name', 'address', 'platform__category', 'platform__type', 'node_id', 
        'platform_id', 'is_active', 'comment', 'org_id'
    ]

    def __init__(self, tree_node: NodeTreeNode, **kwargs):
        self.tree_node = tree_node
        for k, v in kwargs.items():
            setattr(self, k, v)
    
    @property
    def org_name(self):
        Asset.org_name
        org = Organization.get_instance(self.org_id)
        return org.name if org else ''
    

class AssetNodeTree(Tree):
    model_node_only_fields = NodeTreeNode.model_only_fields
    model_asset_only_fields = TreeAsset.model_only_fields


    def __init__(self, assets_scope_q=None, asset_category=None, asset_type=None, org=None):
        self.assets_scope_q = assets_scope_q or Q()
        self.asset_category = asset_category
        self.asset_type = asset_type
        self.org: Organization = org if org else current_org
        super().__init__()
    
    def construct_tree_nodes(self):
        tree_nodes = []
        nodes = Node.objects.filter(org_id=self.org.id).only(*self.model_node_only_fields)
        for node in nodes:
            key = node.key
            if key.isdigit():
                parent_key = None
            else:
                parent_key = ':'.join(key.split(':')[:-1])
            tree_node = NodeTreeNode(
                id=str(node.id),
                key=key, 
                name=node.value, 
                parent_key=parent_key
            )
            tree_nodes.append(tree_node)
        return tree_nodes
    
    def init(self, with_assets_amount=True):
        tree_nodes = self.construct_tree_nodes()
        super().init(tree_nodes)
        if with_assets_amount:
            self.init_tree_nodes_assets_amount()
    
    def assets_scope_queryset(self):
        qs = Asset.objects.filter(org_id=self.org.id)
        if self.assets_scope_q:
            qs = qs.filter(self.assets_scope_q)
        if self.asset_type:
            qs = qs.filter(type=self.asset_type)
        elif self.asset_category:
            qs = qs.filter(category=self.asset_category)
        return qs
    
    def init_tree_nodes_assets_amount(self):
        assets_amounts = self.assets_scope_queryset().values('node_id').annotate(
            assets_amount=Count('id')
        ).values_list('node_id', 'assets_amount')
        assets_amount_mapper = {str(node_id): amount for node_id, amount in assets_amounts}
        for node in self.nodes.values():
            assets_amount = assets_amount_mapper.get(str(node.id), 0)
            node: NodeTreeNode
            node.set_assets_amount(assets_amount)

    def get_tree_assets(self, nodes=None, limit=None):
        if nodes is None:
            id_nodes_mapper = {node.id: node for node in self.get_nodes()}
            filter_node_q = Q()
            limit = limit or 1000
        else:
            id_nodes_mapper = {node.id: node for node in nodes}
            node_ids = list(id_nodes_mapper.keys())
            filter_node_q = Q(node_id__in=node_ids)
            limit = None
        

        tree_assets = []
        assets = self.assets_scope_queryset().filter(filter_node_q).values(*self.model_asset_only_fields)
        assets = assets[:limit] if limit else assets
        for asset in assets:
            kwargs = {k: asset[k] for k in self.model_asset_only_fields}
            tree_node = id_nodes_mapper.get(str(asset['node_id']))
            kwargs.update({'tree_node': tree_node})
            tree_asset = TreeAsset(**kwargs)
            tree_assets.append(tree_asset)
        return tree_assets
    
    def get_nodes(self, with_empty_assets_branch=True):
        if not with_empty_assets_branch:
            self.remove_zero_assets_amount_total_nodes()
        return list(self.nodes.values())
        
    def remove_zero_assets_amount_total_nodes(self):
        for node in list(self.nodes.values()):
            node: NodeTreeNode
            if node.is_root:
                continue
            if node.assets_amount_total > 0:
                continue
            parent: NodeTreeNode = node.parent
            parent.remove_child(node)
            self.nodes.pop(node.key, None)
            for descendant in node.descendants():
                self.nodes.pop(descendant.key, None)
