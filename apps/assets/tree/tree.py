from collections import deque
from common.utils import get_logger, lazyproperty, timeit


__all__ = ['TreeNode', 'Tree']

logger = get_logger(__name__)


class TreeNode(object):

    def __init__(self, _id, key, value, **kwargs):
        self.id = _id
        self.key = key
        self.value = value
        self.children = []
        self.parent = None
        self.children_count_total = 0
    
    def match(self, keyword):
        if not keyword:
            return True
        keyword = str(keyword).strip().lower()
        node_value = str(self.value).strip().lower()
        return keyword in node_value
    
    @lazyproperty
    def parent_key(self):
        if self.is_root:
            return None
        return ':'.join(self.key.split(':')[:-1])
    
    @property
    def is_root(self):
        return self.key.isdigit()

    def add_child(self, child_node: 'TreeNode'):
        child_node.parent = self
        self.children.append(child_node)
    
    def remove_child(self, child_node: 'TreeNode'):
        self.children.remove(child_node)
        child_node.parent = None
    
    @property
    def is_leaf(self):
        return len(self.children) == 0

    @lazyproperty
    def level(self):
        return self.key.count(':') + 1
    
    def get_ancestor_keys(self):
        if self.is_root:
            return []
        
        ancestor_keys = []
        parts = self.key.split(':')
        for i in range(1, len(parts)):
            ancestor_key = ':'.join(parts[:i])
            ancestor_keys.append(ancestor_key)
        return ancestor_keys
    
    def get_descendants(self, node: 'TreeNode'):
        """
        返回指定节点的所有子孙节点（不包含自身），非递归实现，按层级从近到远排序。
        返回列表，空列表表示没有子孙或节点为 None。
        """
        if not node:
            return []

        descendants = []
        dq = deque(node.children)
        while dq:
            cur = dq.popleft()
            descendants.append(cur)
            # 复制 children 以防在遍历过程中被修改
            for ch in list(cur.children):
                dq.append(ch)
        return descendants
    
    @property
    def children_count(self):
        return len(self.children)

    def as_dict(self, simple=True):
        data = {
            'key': self.key,
        }
        if simple:
            return data

        data.update({
            'id': self.id,
            'value': self.value,
            'level': self.level,
            'children_count': self.children_count,
            'is_root': self.is_root,
            'is_leaf': self.is_leaf,
        })
        return data
    
    def print(self, simple=True, is_print_keys=False):
        def info_as_string(_info):
            return ' | '.join(s.ljust(25) for s in _info)
        
        if is_print_keys:
            info_keys = [k for k in self.as_dict(simple=simple).keys()]
            info_keys_string = info_as_string(info_keys)
            print('-' * len(info_keys_string))
            print(info_keys_string)
            print('-' * len(info_keys_string))

        info_values = [str(v) for v in self.as_dict(simple=simple).values()]
        info_values_as_string = info_as_string(info_values)
        print(info_values_as_string)
        print('-' * len(info_values_as_string))


class Tree(object):

    def __init__(self):
        self.root = None
        # { key -> TreeNode }
        self.nodes: dict[TreeNode] = {}

    @property
    def size(self):
        return len(self.nodes)

    @property
    def is_empty(self):
        return self.size == 0

    @property
    def depth(self):
        " 返回树的最大深度，以及对应的节点key "
        if self.is_empty:
            return 0, 0
        node = max(self.nodes.values(), key=lambda node: node.level)
        node: TreeNode
        print(f"max_depth_node_key: {node.key}")
        return node.level

    @property
    def width(self):
        " 返回树的最大宽度，以及对应的层级数 "
        if self.is_empty:
            return 0, 0
        node = max(self.nodes.values(), key=lambda node: node.children_count)
        node: TreeNode
        print(f"max_width_level: {node.level + 1}")
        return node.children_count

    def add_node(self, node: TreeNode):
        if node.is_root:
            self.root = node
            self.nodes[node.key] = node
            return
        parent = self.get_node(node.parent_key)
        if not parent:
            error = f""" Cannot add node {node.key}: parent key {node.parent_key} not found. 
            Please ensure parent nodes are added before child nodes."""
            raise ValueError(error)
        parent.add_child(node)
        self.nodes[node.key] = node

    def get_node(self, key: str) -> TreeNode:
        return self.nodes.get(key)
    
    def remove_node(self, node: TreeNode):
        if node.is_root:
            self.root = None
        else:
            parent: TreeNode = node.parent
            parent.remove_child(node)
        self.nodes.pop(node.key, None)
    
    def search_nodes(self, keyword, only_top_level=False):
        if not keyword:
            return []
        keyword = keyword.strip().lower()
        nodes = {}
        for node in self.nodes.values():
            node: TreeNode
            if not node.match(keyword):
                continue
            nodes[node.key] = node

        if not only_top_level:
            return list(nodes.values())

        # 如果匹配的节点中包含有父子关系的节点，只返回最上一级的父节点
        # TODO: 优化性能
        node_keys = list(nodes.keys())
        children_keys = []
        for node_key in node_keys:
            _children_keys = [k for k in node_keys if k.startswith(f"{node_key}:")]
            children_keys.extend(_children_keys)
        for child_key in children_keys:
            nodes.pop(child_key, None)
        return list(nodes.values())
    
    def remove_nodes_descendants(self, nodes: list[TreeNode]):
        descendants = self.get_nodes_descendants(nodes)
        for node in reversed(descendants):
            self.remove_node(node)
    
    def get_nodes_descendants(self, nodes: list[TreeNode]):
        descendants = []
        for node in nodes:
            ds = node.get_descendants(node)
            descendants.extend(ds)
        return descendants

    def get_nodes_ancestors(self, nodes: list[TreeNode]):
        ancestors = set()
        for node in nodes:
            ancestor_keys = node.get_ancestor_keys()
            _ancestors = self.get_nodes_by_keys(ancestor_keys)
            ancestors.update(_ancestors)
        return list(ancestors)
    
    def get_nodes_by_keys(self, keys):
        nodes = []
        for key in keys:
            node = self.get_node(key)
            if node:
                nodes.append(node)
        return nodes
    
    def get_nodes(self, levels=None):
        nodes = list(self.nodes.values())
        if levels:
            nodes = [ n for n in nodes if n.level in levels ]
        return nodes
    
    def get_node_children(self, key, with_self=False):
        node = self.get_node(key)
        if not node:
            return []
        nodes = []
        if with_self:
            nodes.append(node)
        nodes.extend(node.children)
        return nodes
        
    @timeit
    def _compute_children_count_total(self):
        for node in reversed(list(self.nodes.values())):
            total = 0
            for child in node.children:
                child: TreeNode
                total += child.children_count_total + 1
            node: TreeNode
            node.children_count_total = total
    
    def print(self, count=10, simple=True):
        print('tree_root_key: ', getattr(self.root, 'key', 'No-root'))
        print('tree_size: ', self.size)
        print('tree_depth: ', self.depth)
        print('tree_width: ', self.width)

        is_print_key = True
        for n in list(self.nodes.values())[:count]:
            n: TreeNode
            n.print(simple=simple, is_print_keys=is_print_key)
            is_print_key = False