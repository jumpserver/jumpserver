from common.utils import get_logger, lazyproperty


__all__ = ['TreeNode', 'Tree']

logger = get_logger(__name__)


class TreeNode(object):

    def __init__(self, _id, key, value):
        self.id = _id
        self.key = key
        self.value = value
        self.children = []
        self.parent = None
    
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
        self.parent.children.remove(child_node)
        self.parent = None
    
    def is_leaf(self):
        return len(self.children) == 0

    @lazyproperty
    def level(self):
        return self.key.count(':') + 1
    
    def children_count(self):
        return len(self.children)

    def as_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'level': self.level,
            'children_count': self.children_count(),
            'is_root': self.is_root,
            'is_leaf': self.is_leaf(),
        }
    
    def print(self):
        info = [f"{k}: {v}" for k, v in self.as_dict().items()]
        print(' | '.join(info))


class Tree(object):

    def __init__(self):
        self.root = None
        self.nodes: dict[TreeNode] = {}
    
    def size(self):
        return len(self.nodes)

    def max_depth(self):
        levels = [node.level for node in self.nodes.values()]
        return max(levels) if levels else 0
    
    def max_width(self):
        widths = [node.children_count() for node in self.nodes.values()]
        return max(widths) if widths else 0

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
    
    def print(self, count=10):
        for n in list(self.nodes.values())[:count]:
            n.print()