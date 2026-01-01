from django.db.models import Q, Count

from assets.models import Asset, Node, node
from .tree import Tree, TreeNode, TreeLeaf


class NodeTreeNode(TreeNode):
    model_only_fields = [
        'id', 'key', 'value'
    ]

    def __init__(self, instance, **kwargs):
        super().__init__(**kwargs)
        self.instance = instance

    @property
    def meta(self):
        return {
            'type': 'node',
            'data': {}
        }


class AssetTreeLeaf(TreeLeaf):
    model_only_fields = [
        'node_id', 'id', 'name', 'address', 'category', 'type'
    ]

    def __init__(self, instance, **kwargs):
        super().__init__(**kwargs)
        self.instance = instance
    
    @property
    def meta(self):
        return {
            'type': 'asset',
            'data': {}
        }


class AssetNodeTree(Tree):
    node_model = Node
    leaf_model = Asset

    def __init__(self, assets_scope_q: Q = None, org=None, **kwargs):
        super().__init__(**kwargs)
        self._assets_scope_q = assets_scope_q
        self._org = org
        self._node_id_key_mapper = {}
        self._node_key_id_mapper = {}
        self._node_id_node_mapper = {}
        self._load_complete_nodes()
    
    def _load_complete_nodes(self):
        nodes = Node.objects.filter(org_id=self._org).only(*NodeTreeNode.model_only_fields)
        id_key_mapper = {}
        key_id_mapper = {}
        id_node_mapper = {}
        for n in nodes:
            nid = str(n.id)
            id_key_mapper[nid] = n.key
            key_id_mapper[n.key] = nid
            id_node_mapper[nid] = n
        self._node_id_key_mapper = id_key_mapper
        self._node_key_id_mapper = key_id_mapper
        self._node_id_node_mapper = id_node_mapper

    @property
    def assets_queryset(self):
        q = self._assets_scope_q or Q()
        q &= Q(org_id=self._org.id)
        if self.search_leaf_keyword:
            k = self.search_leaf_keyword
            q &= Q(name__icontains=k) | Q(address__icontains=k)
        queryset = Asset.objects.filter(q)
        return queryset
    
    def construct_nodes(self):
        nid_assets_amount = self.assets_queryset.values('node_id').annotate(
            assets_amount=Count('id')
        ).values_list('node_id', 'assets_amount')
        nid_assets_amount = {
            str(nid): amount for nid, amount in nid_assets_amount
        }
        tree_nodes = []
        for nid, node in self._node_id_node_mapper.items():
            node: Node
            assets_amount = nid_assets_amount.get(nid, 0)
            key = self._node_id_key_mapper.get(nid)
            assert isinstance(key, str), "TreeNode key should is str"
            if key.isdigit():
                parent_key = None
            else:
                parent_key = ':'.join(key.split(':')[:-1]) if ':' in key else None
            tree_node = NodeTreeNode(
                instance=node,
                key=key,
                parent_key=parent_key,
                name=node.name, 
                leaves_amount=assets_amount,
            )
            tree_nodes.append(tree_node)
        return tree_nodes

    def construct_leaves(self, node_key=None):
        tree_leaves = []

        node_id = None
        if node_key:
            node_id = self._node_key_id_mapper.get(node_key)

        q = Q()
        if node_id:
            q &= Q(node_id=node_id)
        
        assets = self.assets_queryset.filter(q).only(*AssetTreeLeaf.model_only_fields)
        for asset in assets:
            node_id = str(asset.node_id)
            parent_key = self._node_id_key_mapper.get(node_id)
            assert parent_key is not None, "TreeLeaf parent key should not be None"
            tree_leaf = AssetTreeLeaf(
                instance=asset,
                key=None,
                parent_key=parent_key,
                name=asset.name,
            )
            tree_leaves.append(tree_leaf)
        return tree_leaves
