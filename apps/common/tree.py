# -*- coding: utf-8 -*-
#


class TreeNode:
    id = ""
    name = ""
    comment = ""
    title = ""
    isParent = False
    pId = ""
    open = False
    iconSkin = ""
    meta = {}

    _tree = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def root(cls):
        return cls(id="#", name='Root', title='Root', isParent=True, open=True)

    def get_parent(self):
        return self._tree.get_node(self.pId)

    def get_parents(self):
        parent = self.get_parent()
        if parent == self._tree.root:
            return []
        parents = [parent]
        parents.extend(parent.get_parents())
        return parents

    def add_child(self, child):
        self._tree.add_node(child, self)

    def __str__(self):
        return '<{}: {}>'.format(self.id, self.name)

    __repr__ = __str__

    def __gt__(self, other):
        return self.id > other.id

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id


class Tree:
    def __init__(self):
        self.nodes = {}
        self.root = TreeNode.root()
        self.root._tree = self

    def add_node(self, node, parent=None):
        node._tree = self

        if not parent:
            parent = self.root
        if parent.id not in self.nodes and parent != self.root:
            raise ValueError("Parent not in tree")
        elif node in parent.get_parents():
            raise ValueError("Parent must not be node parent")
        node.pId = parent.id
        parent.isParent = True
        self.nodes[node.id] = node

    def get_nodes(self):
        return sorted(self.nodes.values())

    def get_node(self, tid):
        return self.nodes.get(tid) or TreeNode.root()
