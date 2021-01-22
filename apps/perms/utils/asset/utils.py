from collections import defaultdict
import copy

from common.struct import Stack
from common.utils.common import timeit
from assets.models import Node


class TreeNode:
    __slots__ = ('id', 'parent_key', 'assets_amount', 'children', 'assets')

    def __init__(self, id, parent_key, assets_amount, children, assets):
        self.id = id
        self.parent_key = parent_key
        self.assets_amount = assets_amount
        self.children = children
        self.assets = assets

    def __str__(self):
        return f'id: {self.id}, parent_key: {self.parent_key}'

    def __repr__(self):
        return self.__str__()


class Tree:
    def __init__(self, nodes, node_asset_id_pairs):
        self.nodes = nodes
        # [(node_id, asset_id)]
        self.node_asset_id_pairs = node_asset_id_pairs
        # node_id --> set(asset_id1, asset_id2)
        self.node_assets_id_mapper = defaultdict(set)
        self.header = None
        self.key_tree_node_mapper = {}

    @timeit
    def build_tree(self, replace_keys=None, replace_source_tree=None, deepcopy=False):
        key_tree_node_mapper = self.key_tree_node_mapper

        # 构建节点资产关系
        node_assets_id_mapper = self.node_assets_id_mapper
        for node_id, asset_id in self.node_asset_id_pairs:
            node_assets_id_mapper[node_id].add(asset_id)

        # 构建 TreeNode
        for node in self.nodes:
            node: Node
            assets = node_assets_id_mapper.pop(node.id, set())
            tree_node = TreeNode(node.id, node.parent_key, 0, [], assets)
            key_tree_node_mapper[node.key] = tree_node

        # 替换节点
        if replace_keys and replace_source_tree:
            replace_source_tree: Tree

            source_key_tree_node_mapper = replace_source_tree.key_tree_node_mapper
            if deepcopy:
                copy_tree_node = lambda x: x
            else:
                copy_tree_node = copy.deepcopy

            for key in replace_keys:
                tree_node = source_key_tree_node_mapper[key]
                key_tree_node_mapper[key] = copy_tree_node(tree_node)

        # 构建 Tree
        headers = []
        for tree_node in key_tree_node_mapper.values():
            if tree_node.parent_key in key_tree_node_mapper:
                key_tree_node_mapper[tree_node.parent_key].children.append(tree_node)
            else:
                headers.append(tree_node)

        if len(headers) != 1:
            raise ValueError(f'Tree get header error: {headers}')

        self.header = headers[0]

    @timeit
    def compute_tree_node_assets_amount(self):
        wait_stack = Stack()
        un_process_stack = Stack()
        # print(f'header {headers[0]}')
        un_process_stack.push(self.header)

        while un_process_stack:
            # print(f'un_process_stack {un_process_stack}')
            tree_node = un_process_stack.pop()
            # print(f'un_process {tree_node}')
            tree_node: TreeNode
            if tree_node.children:
                # print(f'un_process {tree_node} has children')
                wait_stack.push(tree_node)
                # print(f'{tree_node} push to wait_stack')
                for tree_node in tree_node.children:
                    un_process_stack.push(tree_node)
                    continue
            else:
                while True:
                    # 这一步的节点可以直接计算资产数量
                    tree_node.assets_amount = len(tree_node.assets)

                    # 判断还有没有兄弟节点
                    if un_process_stack and tree_node.parent_key == un_process_stack.top.parent_key:
                        # print(f'{tree_node} has brother {un_process_stack.top}')
                        # 有兄弟节点返回到上一层
                        break

                    # 判断有没有祖先节点
                    if not wait_stack:
                        # print(f'{tree_node} has not ancestor')
                        break

                    # 取出父节点
                    tree_node = wait_stack.pop()

                    # 拿出父节点的所有资产，将父节点对资产的引用清除
                    assets = tree_node.assets
                    tree_node.assets = None

                    # 遍历父节点的子节点
                    for child_node in tree_node.children:
                        child_node: TreeNode

                        # 比对哪个集合大
                        if assets > child_node.assets:
                            assets |= child_node.assets
                            tmp = child_node.assets
                            child_node.assets = None
                            del tmp
                        else:
                            child_node.assets |= assets
                            del assets
                            assets = child_node.assets

                    tree_node.assets = assets


def test():
    from orgs.models import Organization
    from assets.models import Node, Asset
    import time

    Organization.default().change_to()

    t1 = time.time()
    nodes = list(Node.objects.exclude(key__startswith='-').only('id', 'key', 'parent_key'))
    node_asset_id_pairs = Asset.nodes.through.objects.all().values_list('node_id', 'asset_id')
    t2 = time.time()

    tree = Tree(nodes, node_asset_id_pairs)
    tree.build_tree()
    tree.compute_tree_node_assets_amount()

    print(f'校对算法准确性 ......')
    for node in nodes:
        tree_node = tree.key_tree_node_mapper[node.key]
        if tree_node.assets_amount != node.assets_amount:
            print(f'ERROR: {tree_node.assets_amount} {node.assets_amount}')
        # print(f'OK {tree_node.asset_amount} {node.assets_amount}')

    print(f'数据库时间: {t2 - t1}')
    return tree
