from collections import defaultdict
import time
import copy

from assets.models import Node, Asset
from common.struct import Stack
from common.utils.common import timeit
from assets.models import Node


class TreeNode:
    __slots__ = ('id', 'parent_key', 'key', 'assets_amount', 'children', 'assets')

    def __init__(self, id, parent_key, key, assets_amount, children, assets):
        self.id = id
        self.parent_key = parent_key
        self.assets_amount = assets_amount
        self.children = children
        self.assets = assets
        self.key = key

    def __str__(self):
        return f'id: {self.id}, parent_key: {self.parent_key}'

    def __repr__(self):
        return self.__str__()


class Tree:
    def __init__(self, nodes, nodekey_assetsid_mapper):
        self.nodes = nodes
        # node_id --> set(asset_id1, asset_id2)
        self.nodekey_assetsid_mapper = nodekey_assetsid_mapper
        self.tree_nodes = []
        self.key_treenode_mapper = {}

    def __getitem__(self, item):
        return self.key_treenode_mapper[item]

    @timeit
    def build_tree(self):
        # 构建 TreeNode
        for node in self.nodes:
            assets = self.nodekey_assetsid_mapper.get(node.key, set())
            tree_node = TreeNode(
                id=node.id, parent_key=node.parent_key,
                key=node.key, assets_amount=0, children=[],
                assets=assets
            )
            self.key_treenode_mapper[tree_node.key] = tree_node
            self.tree_nodes.append(tree_node)

    @timeit
    def compute_tree_node_assets_amount(self):
        stack = Stack()
        sorted_by = lambda node: [int(i) for i in node.key.split(':')]
        tree_nodes = sorted(self.tree_nodes, key=sorted_by)
        # 这个守卫需要添加一下，避免最后一个无法出栈
        guarder = TreeNode('', '', '', 0, [], set())
        tree_nodes.append(guarder)
        for node in tree_nodes:
            # 如果栈顶的不是这个节点的父祖节点，那么可以出栈了，可以计算资产数量了
            while stack.top and not node.key.startswith(f'{stack.top.key}:'):
                _node = stack.pop()
                _node.assets_amount = len(_node.assets)
                self.key_treenode_mapper[_node.key] = _node
                if not stack.top:
                    continue
                stack.top.assets.update(_node.assets)
            stack.push(node)


