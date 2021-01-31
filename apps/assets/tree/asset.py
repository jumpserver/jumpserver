import time
from collections import defaultdict
from data_tree import Data_tree_node
from assets.models import Node, Asset
from django.db.models import ExpressionWrapper, CharField, F
from orgs.utils import tmp_to_org


__all__ = ['AssetTree']


def expression_wrapper_to_char_filed(field_name):
    return ExpressionWrapper(F(field_name), output_field=CharField())


delimiter_for_path = ':'
path_key_of_assets = '.'


class TreeNode(Data_tree_node):
    pass


class AssetTree(object):
    """ 资产树 """

    def __init__(self, org_id):
        self._org_id = org_id
        self._nodes_key = []
        self._root = TreeNode(arg_string_delimiter_for_path=delimiter_for_path)

    def get_node_key_with_all_assets_id_mapping(self):
        """
        获取节点key和节点下所有资产id的映射关系

        About statistics:
        time:
            # nodes: 10000+
            # assets: 250000+
            # time: 20 -30 s
                # _initial_tree: 14s = 4s + 10s
                # _get_node_key_with_all_assets_id_mapping: 7s

        memory:
            # assets: 10000+  =>  3M
            # assets: 10000+ nodes: 10+级 => 30M
        """

        self._initial_tree()
        _mapping = self._get_node_key_with_all_assets_id_mapping()
        return _mapping

    def _get_node_key_with_all_assets_id_mapping(self):
        """ 获取节点key与所有资产id的映射关系 """
        _mapping = defaultdict(list)
        for node_key in self._nodes_key:
            _all_assets_id = self._get_all_assets_id_of_node(node_key=node_key)
            _mapping[node_key] = _all_assets_id
        return _mapping

    def _get_all_assets_id_of_node(self, node_key):
        """ 获取节点下的所有资产id (从树中获取) """
        def _arg_callable_filter(arg_iterable_path, arg_node):
            """
            # such as:
            # node_key=1:1:1, asset_id=asset_id_uuid
            # arg_iterable_path: ['1', '1', '1', '.'] => False
            # arg_iterable_path: ['1', '1', '1', '.', 'asset_id_uuid'] => True
            # arg_iterable_path: ['1', '1', '1', '2'] => False
            """
            if path_key_of_assets in arg_iterable_path:
                if arg_iterable_path[-1] == path_key_of_assets:
                    return False
                else:
                    return True
            else:
                return False

        def _arg_callable_formatter(arg_iterable_path, arg_node):
            """
            # such as (must):
            # arg_iterable_path: ['1', '1', '1', '.', 'asset_id_uuid']
            """
            return arg_iterable_path[-1]

        if not node_key:
            return []

        _tree_node = self._root.get_node_child_at_path(arg_path=node_key)
        if _tree_node is None:
            return []

        _assets_id = _tree_node.get_list_of_pairs_paths_and_node_children(
            arg_bool_search_sub_tree=True,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter,
        )
        return list(set(_assets_id))

    def _initial_tree(self):
        """ 初始化树 """
        t1 = time.time()
        with tmp_to_org(self._org_id):
            # 获取所有的 node_id, node_key
            nodes_id_key = Node.objects.all()\
                .annotate(char_id=expression_wrapper_to_char_filed('id'))\
                .values_list('char_id', 'key')
            nodes_id_key_mapping = dict(nodes_id_key)
            nodes_id = list(nodes_id_key_mapping.keys())
            nodes_key = list(nodes_id_key_mapping.values())
            self._nodes_key = nodes_key

            # 获取所有的 node_id, asset_id (直接)
            nodes_assets_id = Asset.nodes.through.objects\
                .filter(node_id__in=nodes_id)\
                .annotate(char_node_id=expression_wrapper_to_char_filed('node_id'))\
                .annotate(char_asset_id=expression_wrapper_to_char_filed('asset_id'))\
                .values_list('char_node_id', 'char_asset_id')
            nodes_assets_id = list(nodes_assets_id)

        t2 = time.time()

        # 构造所有的 node_id, assets_id (直接) 映射关系
        node_id_assets_id_mapping = defaultdict(set)
        # 获取所有的 asset_id 与 asset_id 的映射关系 (节省内存空间)
        assets_id_mapping = self._get_assets_id_with_themselves_mapping()
        for node_id, asset_id in nodes_assets_id:
            # (节省内存空间, 使用内存中保留的 asset_id 对象)
            _asset_id = assets_id_mapping[asset_id]
            node_id_assets_id_mapping[node_id].add(_asset_id)

        # 构造完整资产树
        for node_id, node_key in nodes_id_key_mapping.items():
            # 添加 node 路径
            tree_node = self._append_path_to_tree_node(tree_node=self._root, arg_path=node_key)
            # 添加 node 下 assets (直接) 的父节点路径
            assets_parent_tree_node = self._append_path_to_tree_node(
                tree_node=tree_node, arg_path=path_key_of_assets
            )
            assets_id = node_id_assets_id_mapping[node_id]
            for asset_id in assets_id:
                # 添加 node 下 assets (直接) 的路径
                self._append_path_to_tree_node(
                    tree_node=assets_parent_tree_node, arg_path=asset_id
                )
        t3 = time.time()

        print('time => _initial_tree => t1-t2: {}, t3-t2: {}'.format(t2-t1, t3-t2))

    def _get_assets_id_with_themselves_mapping(self):
        """ 获取资产id与自身的映射关系 """
        with tmp_to_org(self._org_id):
            assets_id = Asset.objects.all() \
                .annotate(char_id=expression_wrapper_to_char_filed('id')) \
                .values_list('char_id', 'char_id')
            _mapping = dict(assets_id)
            return _mapping

    @staticmethod
    def _append_path_to_tree_node(tree_node: TreeNode, arg_path) -> TreeNode:
        _tree_node = tree_node.append_path(arg_path=arg_path)
        return _tree_node

