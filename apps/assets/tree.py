from common.struct import Stack
from common.utils.common import timeit


class TreeNode:
    __slots__ = ('key', 'assets_amount', 'assets')

    def __init__(self, key, assets_amount, assets):
        self.assets_amount = assets_amount
        self.assets = assets
        self.key = key

    def __str__(self):
        return self.key


class Tree:
    def __init__(self, nodes, nodekey_assetsid_mapper):
        """
        :param nodes: 节点
        :param nodekey_assetsid_mapper:  节点直接资产id的映射 {"key1": set(), "key2": set()}
        """
        self.nodes = nodes
        # node_id --> set(asset_id1, asset_id2)
        self.nodekey_assetsid_mapper = nodekey_assetsid_mapper
        self.tree_nodes = []
        self.key_treenode_mapper = {}

    @timeit
    def build_tree(self):
        # 构建 TreeNode
        for node in self.nodes:
            assets = self.nodekey_assetsid_mapper.get(node.key, set())
            tree_node = TreeNode(key=node.key, assets_amount=0, assets=assets)
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


