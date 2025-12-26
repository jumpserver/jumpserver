from common.utils import get_logger, lazyproperty, timeit


__all__ = ['TreeNode', 'Tree']

logger = get_logger(__name__)


class TreeNode(object):

    def __init__(self, _id, key, value):
        self.id = _id
        self.key = key
        self.value = value
        self.children = []
        self.parent = None
        self.children_count_total = 0
    
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