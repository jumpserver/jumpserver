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
    def __init__(self, nodes, nodekey_assetsid_mapper=None):
        self.nodes = nodes
        # node_id --> set(asset_id1, asset_id2)
        self.nodekey_assetsid_mapper = nodekey_assetsid_mapper
        self.roots = []
        self.key_treenode_mapper = {}

    @classmethod
    def start_test(cls):
        nodes = Node.objects.all()
        mapper = defaultdict(set)
        node_asset_rel = Asset.nodes.through.objects.all()\
            .values_list('node__key', 'asset_id')
        for key, asset_id in node_asset_rel:
            mapper[key].add(str(asset_id))
        tree = cls(nodes, mapper)
        # tree.build_tree()
        # tree.compute_tree_node_assets_amount()
        tree.build_tree_v2()
        print(tree.key_treenode_mapper['2'].assets_amount)
        print(tree.key_treenode_mapper['2:1'].assets_amount)
        print(tree.key_treenode_mapper['2:1:1'].assets_amount)
        return tree

    def __getitem__(self, item):
        return self.key_treenode_mapper[item]

    @timeit
    def build_tree_v2(self):
        if self.nodekey_assetsid_mapper:
            def _get_node_direct_assets(n):
                return self.nodekey_assetsid_mapper.get(n.key, set())
        else:
            def _get_node_direct_assets(n):
                return None
        sorted_by = lambda node: [int(i) for i in node.key.split(':')]
        tree_nodes = []
        stack = Stack()

        # 构建 TreeNode
        for node in self.nodes:
            assets = _get_node_direct_assets(node)
            tree_node = TreeNode(node.id, node.parent_key, node.key, 0, [], assets)
            tree_nodes.append(tree_node)

        tree_nodes = sorted(tree_nodes, key=sorted_by)
        guarder = TreeNode('', '', '', 0, [], set())
        tree_nodes.append(guarder)
        # f = open('/tmp/abc.log', 'w')
        for node in tree_nodes:
            while stack.top and not node.key.startswith(f'{stack.top.key}:'):
                _node = stack.pop()
                _node.assets_amount = len(_node.assets)
                # msg = "出栈: {} 栈顶: {}".format(_node.key, stack.top.key if stack.top else None)
                # print(msg)
                # f.write(msg + '\n')
                self.key_treenode_mapper[_node.key] = _node
                if not stack.top:
                    continue
                # origin_assets_amount = len(stack.top.assets)
                stack.top.assets.update(_node.assets)
                # current_assets_amount = len(stack.top.assets)
                # msg = "节点数量改变: {} {} => {}".format(stack.top.key, origin_assets_amount, current_assets_amount)
                # print(msg)
                # f.write(msg + '\n')
                # time.sleep(1)
                # _node.assets = set()

            # print("入栈: {}".format(node.key))
            # f.write("入栈: {}".format(node.key) + '\n')
            stack.push(node)
            # time.sleep(1)
        # print("剩余: {}".format(', '.join([n.key for n in stack])))

    @timeit
    def build_tree(self):
        if self.nodekey_assetsid_mapper:
            def _get_node_direct_assets(n):
                return self.nodekey_assetsid_mapper.get(n.key, set())
        else:
            def _get_node_direct_assets(n):
                return None

        # 构建 TreeNode
        for node in self.nodes:
            assets = _get_node_direct_assets(node)
            tree_node = TreeNode(node.id, node.parent_key, node.key, 0, [], assets)
            self.key_treenode_mapper[node.key] = tree_node

        # 构建 Tree
        for tree_node in self.key_treenode_mapper.values():
            if tree_node.parent_key in self.key_treenode_mapper:
                self.key_treenode_mapper[tree_node.parent_key].children.append(tree_node)
            else:
                self.roots.append(tree_node)

        self.compute_tree_node_assets_amount()

    @staticmethod
    def compute_a_tree_node_assets_amount(root):
        wait_stack = Stack()
        unprocessed_stack = Stack()
        unprocessed_stack.push(root)

        while unprocessed_stack:
            tree_node = unprocessed_stack.pop()
            if tree_node.children:
                # 父节点压入等待栈
                wait_stack.push(tree_node)
                for node in tree_node.children:
                    # 子节点压入待处理栈，那么必然开始处理子节点
                    unprocessed_stack.push(node)
                    continue
            else:
                while True:
                    # 这一步的节点可以直接计算资产数量
                    tree_node.assets_amount = len(tree_node.assets)

                    # 判断还有没有兄弟节点
                    if unprocessed_stack and tree_node.parent_key == unprocessed_stack.top.parent_key:
                        # print(f'{tree_node} has brother {unprocessed_stack.top}')
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

    @timeit
    def compute_tree_node_assets_amount(self):
        for node in self.roots:
            self.compute_a_tree_node_assets_amount(node)


def get_current_org_full_tree():
    nodes = list(Node.objects.exclude(key__startswith='-').only('id', 'key', 'parent_key'))
    node_asset_id_pairs = Asset.nodes.through.objects.all().values_list('node_id', 'asset_id')
    tree = Tree(nodes, node_asset_id_pairs)
    tree.build_tree()
    return tree


def test():
    from orgs.models import Organization
    from assets.models import Node, Asset
    import time
    Organization.objects.get(id='1863cf22-f666-474e-94aa-935fe175203c').change_to()

    t1 = time.time()
    nodes = list(Node.objects.exclude(key__startswith='-').only('id', 'key', 'parent_key'))
    node_asset_id_pairs = Asset.nodes.through.objects.all().values_list('node_id', 'asset_id')
    t2 = time.time()
    node_asset_id_pairs = list(node_asset_id_pairs)
    tree = Tree(nodes,  node_asset_id_pairs)
    tree.build_tree()
    tree.nodes = None
    tree.node_asset_id_pairs = None
    import pickle
    d = pickle.dumps(tree)
    print('------------', len(d))
    return tree
    tree.compute_tree_node_assets_amount()

    print(f'校对算法准确性 ......')
    for node in nodes:
        tree_node = tree.key_tree_node_mapper[node.key]
        if tree_node.assets_amount != node.assets_amount:
            print(f'ERROR: {tree_node.assets_amount} {node.assets_amount}')
        # print(f'OK {tree_node.asset_amount} {node.assets_amount}')

    print(f'数据库时间: {t2 - t1}')
    return tree
