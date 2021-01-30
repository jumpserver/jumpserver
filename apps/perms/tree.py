from typing import List
from common.struct import Stack

from perms.models import UserAssetGrantedTreeNodeRelation
from assets.tree import Tree, TreeNode


NodeFrom = UserAssetGrantedTreeNodeRelation.NodeFrom


class GrantedTree(Tree):
    def get_node_descendant(self, key, id_node_mapper):
        granted = []
        asset_granted = []

        def _group_node(id):
            node: UserAssetGrantedTreeNodeRelation
            node = id_node_mapper[id]
            if node.node_from == NodeFrom.granted:
                granted.append(node)
            elif node.node_from == NodeFrom.asset:
                asset_granted.append(node)

        stack = Stack()
        node: TreeNode
        node = self.key_tree_node_mapper[key]
        stack.push(node)

        while stack:
            node = stack.pop()
            _group_node(node.id)
            if node.children:
                for n in node.children:
                    stack.push(n)

        return granted, asset_granted
