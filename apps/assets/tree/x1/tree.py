from xpack.plugins.interface import meta
from abc import abstractmethod
from assets.models import Asset, Node
from collections import defaultdict

from common.utils import lazyproperty

__all__ = [ 'TreeNode', 'TreeLeaf', 'Tree' ]

class TreeNode:

    def __init__(self, key, parent_key, name, leaves_amount=0):
        ## need to serialize fields
        self.id = key
        self.key = key # leaf key is None, parent_key
        self.name = name
        self.open = True
        self.parent = None
        self.parent_key = parent_key
        self.is_leaf = False
        self.children = []
        self.leaves = []
        self.leaves_amount = leaves_amount
    
    @property
    def is_root(self):
        return self.parent_key is None
    
    def add_child(self, child: 'TreeNode'):
        child.parent = self
        self.children.append(child)
    
    def add_leaf(self, leaf: 'TreeLeaf'):
        leaf.parent = self
        self.leaves.append(leaf)
    
    def matched(self, keyword):
        if not keyword:
            return True
        keyword = str(keyword).strip().lower()
        value = str(self.name).strip().lower()
        return keyword in value
    
    def is_parent(self):
        return len(self.children) > 0 or len(self.leaves) > 0

    @property
    def meta(self) -> dict:
        ''' 元数据
        {
            'type': None,
            'data': {}
        }
        '''
        raise NotImplementedError

    @lazyproperty
    def leaves_amount_total(self):
        count = self.leaves_amount
        for child in self.children:
            child: TreeNode
            count += child.leaves_amount_total
        return count


class TreeLeaf(TreeNode):

    def __init__(self, id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id
        self.key = None
        self.is_leaf = True
        self.open = False
    

class Tree:

    def __init__(self, search_node_keyword=None, search_leaf_keyword=None, with_leaves=False):
        self.root = None
        self.tree = dict()
        self.nodes = dict()
        self.leaves = []

        self.search_node_keyword = search_node_keyword
        self.search_leaf_keyword = search_leaf_keyword
        self.with_leaves = with_leaves
        self.with_leaves_amount = True

    def build(self):
        self.build_nodes()
        if self.with_leaves:
            self.build_leaves()
    
    def build_nodes(self):
        nodes = self.construct_nodes()
        self.add_nodes(nodes)

    def build_leaves(self, node_key=None):
        leaves = self.construct_leaves(node_key=node_key)
        self.add_leaves(leaves)
    
    @abstractmethod
    def construct_nodes(self):
        # Node.objects.all()
        raise NotImplementedError

    @abstractmethod
    def construct_leaves(self, node_key=None):
        # Asset.objects.all()
        raise NotImplementedError

    def expand_node(self, node_key, with_leaves=False):
        node = self.get_node(node_key=node_key)
        node: TreeNode
        if with_leaves:
            # 包含资产
            if not self.with_leaves:
                # 树中没有资产，构建资产
                self.build_leaves(node_key=node_key)
        return node.children + node.leaves
    
    def search_nodes(self, keyword):
        keyword = self.search_node_keyword
        matched_nodes = {}
        for node in self.tree.values():
            node: TreeNode
            if not node.matched(keyword):
                continue
            matched_nodes[node.key] = node
        
        to_remove_keys = set()
        matched_keys = list(matched_nodes.keys())
        for mk in matched_keys:
            descendants_keys = [k for k in matched_keys if k.startswith(f"{mk}:")]
            to_remove_keys.update(descendants_keys)

        for ck in to_remove_keys:
            matched_nodes.pop(ck, None)
        top_nodes = matched_nodes.values()
        return top_nodes
        
    def get_nodes(self):
        if not self.search_node_keyword:
            return list(self.tree.values())
        searched_nodes = self.search_nodes(keyword=self.search_node_keyword)
        nodes = self.get_nodes_ancestors(searched_nodes)
        return nodes + searched_nodes
    
    def get_nodes_ancestors(self, nodes: list[TreeNode]):
        ancestors = set()
        for node in nodes:
            n_ancestors = self.get_node_ancestors(node)
            ancestors.update(n_ancestors)
        return list(ancestors)
    
    def get_node_ancestors(self, node: TreeNode):
        if node.is_root:
            return []
        ancestors = []
        parent = node.parent
        while parent:
            parent: TreeNode
            ancestors.append(parent)
            if parent.is_root:
                break
            parent = parent.parent
        return ancestors

    def add_nodes(self, nodes: list[TreeNode]):
        self.nodes = {n.key: n for n in nodes}
        for node in nodes:
            self.add_node(node)
    
    def add_node(self, node: TreeNode):
        parent = self.nodes.get(node.parent_key)
        if not parent:
            self.root = node
            self._add_node(node)
            return
        
        parent: TreeNode
        if self.exist(parent.key):
            self.add_node(parent)
            
        self._add_node(node)
    
    def exist(self, node_key):
        return node_key in self.tree
    
    def _add_node(self, node: TreeNode):
        if node.is_root:
            self.tree[node.key] = node
            return

        parent = self.get_node(node_key=node.parent_key)
        assert isinstance(parent, TreeNode) , f"Parent node {node.parent_key} not found for node {node.key}"
        parent.add_child(node)
        self.tree[node.key] = node
    
    def get_node(self, node_key=None):
        return self.tree.get(node_key)

    def add_leaves(self, leaves):
        for leaf in leaves:
            self.add_leaf(leaf)

    def add_leaf(self, leaf: TreeLeaf):
        parent = self.get_node(leaf.parent_key)
        assert isinstance(parent, TreeNode) , f"Parent node {leaf.parent_key} not found for leaf {leaf.key}"
        parent.add_leaf(leaf)


# 初始化树
# 展开某个树节点
# 搜索树中的节点
# 搜索树中的叶子

"""

树的节点，是根据叶子来限定范围的

不同的树，叶子类型不同，查询叶子的 queryset 也不同

叶子是从数据库中来的
节点也是从数据库中来的
在数据库模型中，本质上节点是叶子的一个属性
我们获取树的出发点，首先是符合条件的叶子

初始化一颗完整树时，节点的范围是由叶子的范围决定的

只搜索叶子时，树需要重新初始化，因为叶子的范围变化了
只搜索节点时，树不需要重新初始化，因为叶子的范围没有变化
既搜索节点:又搜索叶子时，首先查询出符合条件的节点，然后根据符合条件的节点，查询出符合条件的叶子，然后根据叶子生成树

展开一个节点时，本质上展开的是一颗搜索树上的一个节点，返回节点的子节点和叶子

初始化一颗树有2种情况：
1. 初始化只包含节点的树
2. 初始化既包含节点，又包含某些节点的叶子的树


因为每一颗树的节点都必须包含它的叶子数量和叶子总数量

查询每个节点下叶子数量，必须用一条 SQL 语句完成，性能才能接受

因为一颗树中的所有叶子是不计其数的，
    所以在初始化一颗完整树时，不能获取出所有叶子，只能获取某个节点下的叶子
    在初始化一颗搜索叶子的树时，虽然理论上应该要返回所有符合条件的叶子，但是为了避免叶子数量巨大，所以必须限制返回的叶子数量


核心问题：
如何根据一些扁平化数据的简单父子关系，构建出一颗树中的完整父子关系
如何定义叶子的查询范围
如何定义节点的查询范围


初始化一颗树时，首先是确定节点的范围，然后在节点范围的基础上，确定叶子的范围。
一定是两者的交集，来构建树
如：node_ids, Asset.objects.filter(node_id__in=node_ids).filter(id__in=[])
其中查询叶子时，一定有节点下不包含叶子的情况，所以要区分是否包含叶子总数量为0的节点，即所谓空节点

# Tips: 查询每个节点下叶子总数量比较慢（所以才改成一个资产只能属于一个节点，如果属于多个节点时，就不是树的数据结构了，而是图的数据结构，复杂度会高很多）

树初始化完之后，一定是一颗包含所有节点完整树

# ...
queryset 分三部分

完整树
nodes = nodes_queryset
assets = nodes & assets_queryset


搜索树
nodes = tree:nodes and search_nodes_queryset
assets = nodes and search_assets_queryset

展开完整树的某个节点
nodes = tree:nodes:children 
assets = tree:assets:expand_nodes_queryset

展开搜索树的某个节点
nodes = search_tree:nodes:children
assets = search_tree:assets:expand_nodes_queryset
"""



class XTree:
    tree_nodes = {}

    # build tree
    def build(self, search_leaf_keyword=None, with_leaves_nodes_keys=None):
        self.build_tree_nodes()
        self.compute_tree_nodes_leaves_amount_total(search_leaf_keyword=search_leaf_keyword)
        self.load_tree_nodes_leaves(nodes_keys=with_leaves_nodes_keys, search_leaf_keyword=search_leaf_keyword)
        self.remove_empty_tree_nodes_if_need()
    
    def build_tree_nodes(self):
        nodes = self.query_and_construct_tree_nodes()
        self.add_tree_nodes_to_tree(nodes=nodes)
    
    def query_and_construct_tree_nodes(self) -> list[TreeNode]:
        raise NotImplementedError

    def add_tree_nodes_to_tree(self, nodes: list[TreeNode]):
        pass

    def compute_tree_nodes_leaves_amount_total(self, search_leaf_keyword=None):
        nodes_leaves_amount = self.query_tree_nodes_leaves_amount(search_leaf_keyword=search_leaf_keyword)
        for node, leaves_amount in nodes_leaves_amount:
            node: TreeNode
            node.set_leaves_amount(leaves_amount)
        for node in self.tree_nodes.values():
            node: TreeNode
            node.compute_leaves_amount_total()
    
    def query_tree_nodes_leaves_amount(self, search_leaf_keyword=None) -> list[tuple[TreeNode, int]]:
        raise NotImplementedError
    
    def load_tree_nodes_leaves(self, nodes_keys=None, search_leaf_keyword=None):
        leaves = self.query_and_construct_tree_nodes_leaves(nodes_keys=nodes_keys, search_leaf_keyword=search_leaf_keyword)
        leaves: list[TreeLeaf]
        self.add_leaves_to_tree_nodes(leaves=leaves)

    def query_and_construct_tree_nodes_leaves(self, nodes_keys=None, search_leaf_keyword=None) -> list[TreeLeaf]:
        raise NotImplementedError

    def add_leaves_to_tree_nodes(self, leaves: list[TreeLeaf]):
        pass

    def remove_empty_tree_nodes_if_need(self):
        pass

    # get tree nodes
    def get_nodes(self, nodes_keys=None, with_leaves=False):
        nodes_keys = nodes_keys or self.tree_nodes.keys()
        for node_key in nodes_keys:
            node = self.get_node(node_key=node_key)
            if not node:
                continue
            node: TreeNode
            if with_leaves:
                yield node.children + node.leaves
            else:
                yield node.children
            
    def get_node(self, node_key=None):
        return self.tree_nodes.get(node_key)