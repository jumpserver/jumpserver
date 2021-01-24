import abc
from data_tree import Data_tree_node

from assets.models import Asset, Node

from common.utils import lazyproperty, timeit
from collections import defaultdict

from orgs.utils import tmp_to_org

delimiter_for_path = ':'
delimiter_for_key_of_asset = '.'


class BaseNodeAssetTree(object):
    def __init__(self, *args, **kwargs):
        self._root = Data_tree_node(arg_string_delimiter_for_path=delimiter_for_path)

    # method of abstract
    @abc.abstractmethod
    def initial(self, *args, **kwargs):
        raise NotImplemented

    @staticmethod
    @abc.abstractmethod
    def _arg_callable_path_filter_of_node(arg_iterable_path, arg_node):
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def _arg_callable_path_filter_of_asset(arg_iterable_path, arg_node):
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def _arg_callable_path_formatter_of_asset_id(arg_iterable_path, arg_node):
        raise NotImplementedError

    # method of data tree node

    @staticmethod
    def _append_path_of_data_tree_node(date_tree_node: Data_tree_node, arg_path, **kwargs):
        arg_node = kwargs.get('arg_node')
        data_tree_node_of_path = date_tree_node.append_path(arg_path=arg_path, arg_node=arg_node)
        return data_tree_node_of_path

    @staticmethod
    def _arg_callable_path_formatter(arg_iterable_path, arg_node):
        return delimiter_for_path.join(arg_iterable_path)

    def _paths_of_data_tree_node(self, data_tree_node: Data_tree_node, **kwargs):
        """ 获取 Data_tree_node 节点的路径 """
        _arg_bool_search_sub_tree = kwargs.get('arg_bool_search_sub_tree', True)
        _arg_callable_filter = kwargs.get('arg_callable_filter')
        _arg_callable_formatter = kwargs.get('arg_callable_formatter')
        _arg_callable_formatter = _arg_callable_formatter or self._arg_callable_path_formatter

        paths = data_tree_node.get_list_of_pairs_paths_and_node_children(
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_node_children(self, node_key=None, immediate=False):
        """
        return: 返回节点的子节点的路径
        arg: node_key - 节点key
        arg: immediate - 是否是直接子节点
        """
        if node_key is None:
            data_tree_node = self._root
        else:
            data_tree_node = self._root.get_node_child_at_path(node_key)

        if immediate:
            _arg_bool_search_sub_tree = False
        else:
            _arg_bool_search_sub_tree = True

        paths = self._paths_of_data_tree_node(
            data_tree_node=data_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=self._arg_callable_path_filter_of_node
        )
        return paths

    def paths_of_nodes(self):
        """ 获取所有节点的路径 """
        paths = self.paths_of_node_children(node_key=None)
        return paths

    def paths_of_node_assets(self, node_key, immediate, **kwargs):
        """
        return: 返回节点的资产的路径
        arg: node_key - 节点key
        arg: immediate - 是否是直接资产
        """
        _arg_callable_formatter = kwargs.get('arg_callable_formatter')

        if immediate:
            # Such as: node_key:.
            _data_tree_node_path = '{}{}{}'.format(
                node_key, delimiter_for_path, delimiter_for_key_of_asset
            )
            _arg_bool_search_sub_tree = False
            _arg_callable_filter = None
        else:
            _data_tree_node_path = node_key
            _arg_bool_search_sub_tree = True
            _arg_callable_filter = self._arg_callable_path_filter_of_asset

        data_tree_node = self._root.get_node_child_at_path(_data_tree_node_path)
        paths = self._paths_of_data_tree_node(
            data_tree_node=data_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    # method of get

    def get_nodes_key(self):
        nodes_key = self.paths_of_nodes()
        return nodes_key

    def get_assets_id_of_node(self, node_key=None, immediate=False):
        assets_id = self.paths_of_node_assets(
            node_key=node_key, immediate=immediate,
            arg_callable_formatter=self._arg_callable_path_formatter_of_asset_id
        )
        return set(assets_id)

    # method of count

    def count_of_node_assets(self, node_key, immediate=False):
        """ 统计节点下资产数量 """
        assets_id = self.get_assets_id_of_node(node_key=node_key, immediate=immediate)
        return len(assets_id)

    @timeit
    def count_pairs_of_node_assets(self, nodes_key, immediate=False):
        """ 成对统计节点下所有资产数量"""
        count_pairs = defaultdict(int)
        for node_key in nodes_key:
            assets_count = self.count_of_node_assets(node_key=node_key, immediate=immediate)
            count_pairs[node_key] = assets_count
        return count_pairs

    @timeit
    def count_paris_of_node_assets_for_tree(self, immediate=False):
        """ 成对统计所有节点下所有资产数量"""
        nodes_key = self.get_nodes_key()
        count_pairs = self.count_pairs_of_node_assets(nodes_key=nodes_key, immediate=immediate)
        return count_pairs


class OrgNodeAssetTree(BaseNodeAssetTree):

    def __init__(self, org_id, *args, **kwargs):
        self._org_id = org_id
        super().__init__(*args, **kwargs)

    def initial(self):
        with tmp_to_org(self._org_id):
            nodes = list(Node.objects.all().values_list('id', 'key'))
            nodes_id = [str(node_id) for node_id, node_key in nodes]
            nodes_assets_id = Node.assets.through.objects.filter(node_id__in=nodes_id).values_list(
                'node_id', 'asset_id'
            )
            nodes_assets_id_mapping = defaultdict(set)
            for node_id, asset_id in nodes_assets_id:
                nodes_assets_id_mapping[str(node_id)].add(str(asset_id))

        for node_id, node_key in nodes:
            path_of_node = '{}{}{}'.format(
                node_key, delimiter_for_path, delimiter_for_key_of_asset
            )
            data_tree_node = self._append_path_of_data_tree_node(self._root, arg_path=path_of_node)
            for asset_id in nodes_assets_id_mapping[str(node_id)]:
                self._append_path_of_data_tree_node(data_tree_node, arg_path=asset_id)

    @staticmethod
    def _arg_callable_path_filter_of_node(arg_iterable_path, arg_node):
        if delimiter_for_key_of_asset in arg_iterable_path:
            return False
        return True

    @staticmethod
    def _arg_callable_path_filter_of_asset(arg_iterable_path, arg_node):
        if delimiter_for_key_of_asset not in arg_iterable_path:
            return False
        if arg_iterable_path[-1] == delimiter_for_key_of_asset:
            return False
        return True

    @staticmethod
    def _arg_callable_path_formatter_of_asset_id(arg_iterable_path, arg_node):
        return arg_iterable_path[-1]


