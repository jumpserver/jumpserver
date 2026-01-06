__all__ = ['TreeNode', 'Tree']


class TreeNode:

    def __init__(self, key, name, parent_key=None):
        self.key = key
        self.name = name
        self.parent_key = parent_key
        self.parent = None
        self.children = []
    
    def add_child(self, child: 'TreeNode') -> None:
        child.parent = self
        self.children.append(child)


class Tree:

    def __init__(self):
        self.root = None
        self.nodes = {}

    def init(self, nodes: list[TreeNode]) -> None:
        for node in nodes:
            self.nodes[node.key] = node
        
        for node in nodes:
            if node.parent_key is None:
                self.root = node
                continue
            parent = self.nodes.get(node.parent_key)
            if not parent:
                raise ValueError(f'Parent with key {node.parent_key} not found for node {node.key}')
            parent: TreeNode
            parent.add_child(node)
    
    def get_node(self, key) -> TreeNode | None:
        return self.nodes.get(key)
