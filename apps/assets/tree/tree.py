
__all__ = ['TreeNode', 'Tree']


class TreeNode:

    def __init__(self, key, name, parent_key):
        self.key = key
        self.name = name
        self.parent_key = parent_key
        self.parent = None
        self.children = []
    
    def add_child(self, child: 'TreeNode'):
        child.parent = self
        self.children.append(child)
    
    def remove_child(self, child: 'TreeNode'):
        self.children.remove(child)
        child.parent = None
    
    def descendants(self) -> list['TreeNode']:
        nodes = []
        for child in self.children:
            child: TreeNode
            nodes.append(child)
            nodes.extend(child.descendants())
        return nodes
    
    def ancestors(self) -> list['TreeNode']:
        node = self
        ancestors = []
        while node.parent:
            ancestors.append(node.parent)
            node = node.parent
        ancestors.reverse()
        return ancestors

    @property
    def is_root(self):
        return self.parent is None
    
    @property
    def level(self):
        level = 1
        node = self
        while node.parent:
            level += 1
            node = node.parent
        return level
    
    @property
    def is_leaf(self):
        return len(self.children) == 0


class Tree:

    def __init__(self):
        self.root = None
        self.nodes = {}

    def init(self, nodes: list[TreeNode]) -> None:
        for node in nodes:
            self.nodes[node.key] = node
        for node in nodes:
            self.add_node(node)
    
    def add_node(self, node: TreeNode) -> None:
        if node.parent_key is None:
            self.root = node
            return

        parent = self.nodes.get(node.parent_key)
        if parent:
            parent: TreeNode
            parent.add_child(node)
        else:
            raise ValueError(f'Parent with key {node.parent_key} not found for node {node.key}')
    
    def get_node(self, key) -> TreeNode | None:
        return self.nodes.get(key)
    
    def get_nodes(self) -> list[TreeNode]:
        return list(self.nodes.values())
    
    def pre_order_traversal(self, node: TreeNode = None) -> list[TreeNode]:
        if node is None:
            node = self.root
        
        if not node:
            return []
        
        result = [node]
        for child in node.children:
            result.extend(self.pre_order_traversal(child))
        
        return result