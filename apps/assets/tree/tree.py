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
        if not simple:
            data.update({
                'id': self.id,
                'value': self.value,
                'level': self.level,
                'children_count': self.children_count,
                'is_root': self.is_root,
                'is_leaf': self.is_leaf,
            })
        return data
    
    def print(self, simple=True):
        info = [f"{k}: {v}" for k, v in self.as_dict(simple=simple).items()]
        print(' | '.join(info))


class Tree(object):

    def __init__(self):
        self.root = None
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
        logger.debug(f"Max depth node key: {node.key}")
        return node.level

    @property
    def width(self):
        " 返回树的最大宽度，以及对应的层级数 "
        if self.is_empty:
            return 0, 0
        node = max(self.nodes.values(), key=lambda node: node.children_count)
        node: TreeNode
        logger.debug(f"Max width level: {node.level + 1}")
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
    
    def print(self, count=10, simple=True):
        print('Tree root: ', getattr(self.root, 'key', 'No-root'))
        print('Tree size: ', self.size)
        print('Tree depth: ', self.depth)
        print('Tree width: ', self.width)

        for n in list(self.nodes.values())[:count]:
            n: TreeNode
            n.print(simple=simple)