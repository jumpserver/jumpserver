from typing import List
from common.struct import Stack

from perms.models import UserGrantedMappingNode
from assets.tree import Tree


class GrantedTree(Tree):
    def get_node_descendant(self, key, id_node_mapper):
        mnode: UserGrantedMappingNode

        granted = []
        asset_granted = []

        def _group_node(id):
            mnode = id_node_mapper[id]
            if mnode.granted:
                granted.append(mnode)
            elif mnode.asset_granted:
                asset_granted.append(mnode)

        stack = Stack()
        node = self.key_tree_node_mapper[key]
        stack.push(node)

        while stack:
            node = stack.pop()
            _group_node(node.id)
            if node.children:
                for n in node.children:
                    stack.push(n)

        return granted, asset_granted
