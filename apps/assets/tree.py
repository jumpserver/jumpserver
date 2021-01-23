from data_tree import Data_tree_node

from assets.models import Asset, Node

from common.utils import lazyproperty, timeit
from collections import defaultdict

from orgs.utils import tmp_to_org


class NodeAssetTree(object):
    def __init__(self, org_id):
        self._org_id = org_id
        self._root = Data_tree_node(arg_string_delimiter_for_path=':')

        self._nodes = list()
        self._nodes_assets_mapping = defaultdict(set)
        self.initial()

    # initial tree
    @timeit
    def _pre_initial_tree(self):
        with tmp_to_org(self._org_id):
            nodes = list(Node.objects.values_list('id', 'key'))
            nodes_id = [str(node[0]) for node in nodes]
            nodes_assets = Node.assets.through.objects.filter(node_id__in=nodes_id).values_list(
                'node_id', 'asset_id'
            )
            nodes_assets_mapping = defaultdict(set)
            for node_id, asset_id in nodes_assets:
                nodes_assets_mapping[str(node_id)].add(str(asset_id))

            self._nodes = nodes
            self._nodes_assets_mapping = nodes_assets_mapping

    @timeit
    def _initial_tree(self):
        for node_id, node_key in self._nodes:
            tree_node: Data_tree_node = self._root.append_path(
                arg_path='{}:.'.format(node_key), arg_bool_path_is_absolute=True
            )
            for asset_id in self._nodes_assets_mapping[str(node_id)]:
                tree_node.append_path(arg_path=asset_id, arg_bool_path_is_absolute=False)

    @timeit
    def initial(self):
        """ 初始化节点资产树 """
        self._pre_initial_tree()
        self._initial_tree()

    # method of paths

    @staticmethod
    def _paths_of_data_tree_node(data_tree_node: Data_tree_node, **kwargs):
        """ 获取 Data_tree_node 节点的路径 """
        def _arg_callable_formatter(arg_iterable_path, arg_node):
            return ':'.join(arg_iterable_path)

        arg_bool_search_sub_tree = kwargs.get('arg_bool_search_sub_tree', True)
        arg_callable_filter = kwargs.get('arg_callable_filter')
        arg_callable_formatter = kwargs.get('arg_callable_formatter') or _arg_callable_formatter

        paths = data_tree_node.get_list_of_pairs_paths_and_node_children(
            arg_bool_search_sub_tree=arg_bool_search_sub_tree,
            arg_callable_filter=arg_callable_filter,
            arg_callable_formatter=arg_callable_formatter
        )
        return paths

    def _paths_of_node_children(self, node_key=None, immediate=False):
        """ 获取节点下的子节点路径 """
        def arg_callable_filter(arg_iterable_path, arg_node):
            if '.' in arg_iterable_path:
                return False
            return True

        if immediate:
            _arg_bool_search_sub_tree = False
        else:
            _arg_bool_search_sub_tree = True

        if node_key is None:
            data_tree_node = self._root
        else:
            data_tree_node = self._root.get_node_child_at_path(node_key)

        paths = self._paths_of_data_tree_node(
            data_tree_node=data_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=arg_callable_filter
        )
        return paths

    @timeit
    def paths_of_nodes(self):
        """ 获取所有节点的路径 """
        paths = self._paths_of_node_children(node_key=None)
        return paths

    def paths_of_node_children(self, node_key, immediate):
        """
        return: 返回节点的子节点的路径
        arg: node_key - 节点key
        arg: immediate - 是否是直接子节点
        """
        paths = self._paths_of_node_children(node_key=node_key, immediate=immediate)
        return paths

    def _paths_of_node_assets(self, node_key, immediate, include_parent_path):
        """ 获取节点下的资产路径 """
        def arg_callable_filter(arg_iterable_path, arg_node):
            if '.' not in arg_iterable_path:
                return False
            if arg_iterable_path[-1] == '.':
                return False
            return True

        def arg_callable_formatter(arg_iterable_path, arg_node):
            return arg_iterable_path[-1]

        if include_parent_path:
            _arg_callable_formatter = None
        else:
            _arg_callable_formatter = arg_callable_formatter

        if immediate:
            _data_tree_node_path = '{}:.'.format(node_key)
            _arg_bool_search_sub_tree = False
            _arg_callable_filter = None
        else:
            _data_tree_node_path = node_key
            _arg_bool_search_sub_tree = True
            _arg_callable_filter = arg_callable_filter

        data_tree_node = self._root.get_node_child_at_path(_data_tree_node_path)
        paths = self._paths_of_data_tree_node(
            data_tree_node=data_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_node_assets(self, node_key, immediate=False, include_parent_path=False):
        """
        return: 返回节点的资产的路径
        arg: node_key - 节点key
        arg: immediate - 是否是直接资产
        arg: include_parent_path - 是否包含父节点路径
        """
        paths = self._paths_of_node_assets(
            node_key=node_key, immediate=immediate, include_parent_path=include_parent_path
        )
        return paths

    # method of count

    def count_of_node_assets(self, node_key, immediate=False):
        """ 统计节点下资产数量 """
        paths = self.paths_of_node_assets(node_key=node_key, immediate=immediate)
        return len(set(paths))

    @timeit
    def count_pairs_of_node_assets(self, nodes_key, immediate=False):
        """ 成对统计所有节点下所有资产数量"""
        count_pairs = defaultdict(int)
        for node_key in nodes_key:
            assets_count = self.count_of_node_assets(node_key=node_key, immediate=immediate)
            count_pairs[node_key] = assets_count
        return count_pairs

    @timeit
    def count_paris_of_node_assets_for_tree(self, immediate=False):
        nodes_key = self.paths_of_nodes()
        count_pairs = self.count_pairs_of_node_assets(nodes_key=nodes_key, immediate=immediate)
        return count_pairs
