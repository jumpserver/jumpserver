import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'jumpserver.settings')
django.setup()

import abc
import time
import copy
from data_tree import Data_tree_node
from assets.models import Asset, Node
from perms.models import AssetPermission
from common.utils import lazyproperty, timeit
from collections import defaultdict
from orgs.utils import tmp_to_org

delimiter_for_path = ':'
delimiter_for_key_of_asset = '.'


class BaseNodeAssetTree(object):
    def __init__(self, *args, **kwargs):
        self._root = Data_tree_node(arg_string_delimiter_for_path=delimiter_for_path)

    @abc.abstractmethod
    def initial(self, *args, **kwargs):
        raise NotImplemented

    @staticmethod
    def _append_path_of_data_tree_node(date_tree_node: Data_tree_node, arg_path, **kwargs):
        arg_node = kwargs.get('arg_node')
        data_tree_node_of_path = date_tree_node.append_path(arg_path=arg_path, arg_node=arg_node)
        return data_tree_node_of_path

    def _get_data_tree_node_at_path(self, arg_path) -> Data_tree_node:
        data_tree_node = self._root.get_node_child_at_path(arg_path=arg_path)
        return data_tree_node

    @staticmethod
    def _paths_of_data_tree_node(data_tree_node: Data_tree_node, **kwargs):
        """ 获取 Data_tree_node 节点的路径 """

        _arg_bool_search_sub_tree = kwargs.get('arg_bool_search_sub_tree', True)
        _arg_bool_search_entire_tree = kwargs.get('arg_bool_search_entire_tree', False)
        _arg_callable_filter = kwargs.get('arg_callable_filter')
        _arg_callable_formatter = kwargs.get('arg_callable_formatter')

        paths = data_tree_node.get_list_of_pairs_paths_and_node_children(
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_bool_search_entire_tree=_arg_bool_search_entire_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_node_children(self, node_key=None, level=None):
        """
        return: 返回节点的子节点的路径
        arg: node_key - 节点key
        arg: immediate - 是否是直接子节点
        """

        def arg_callable_filter_of_node_key(arg_iterable_path, arg_node):
            return ''.join(arg_iterable_path).isdigit()

        def arg_callable_filter_of_node_key_level(arg_iterable_path, arg_node):
            if not arg_callable_filter_of_node_key(arg_iterable_path, arg_node):
                return False
            return level >= len(arg_iterable_path)

        def arg_callable_formatter_of_node_key(arg_iterable_path, arg_node):
            return delimiter_for_path.join(arg_iterable_path)

        def arg_callable_formatter_of_node_key_relative_path(arg_iterable_path, arg_node):
            arg_iterable_path.insert(0, node_key)
            return delimiter_for_path.join(arg_iterable_path)

        if node_key is None:
            data_tree_node = self._root
            _arg_callable_formatter = arg_callable_formatter_of_node_key
        else:
            data_tree_node = self._root.get_node_child_at_path(node_key)
            if data_tree_node is None:
                return []
            _arg_callable_formatter = arg_callable_formatter_of_node_key_relative_path

        if level is None:
            _arg_bool_search_sub_tree = True
            _arg_callable_filter = arg_callable_filter_of_node_key
        else:
            assert isinstance(level, int) and level >= 1, '`level` should be of type int and >= 1'
            if level == 1:
                _arg_bool_search_sub_tree = False
                _arg_callable_filter = arg_callable_filter_of_node_key
            else:
                _arg_bool_search_sub_tree = True
                _arg_callable_filter = arg_callable_filter_of_node_key_level

        paths = self._paths_of_data_tree_node(
            data_tree_node=data_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def get_node_children_key(self, node_key, level=None):
        nodes_key = self.paths_of_node_children(node_key, level=level)
        return nodes_key

    def get_nodes_key(self, level=None):
        nodes_key = self.get_node_children_key(node_key=None, level=level)
        return nodes_key

    def get_node(self, node_key):
        node = self._get_data_tree_node_at_path(arg_path=node_key)
        return node

    def paths_of_node_assets(self, node_key, immediate, only_asset_id=False):
        """
        return: 返回节点的资产的路径
        arg: node_key - 节点 key
        arg: immediate - 是否是直接资产
        arg: only_asset_id - 是否只返回资产id
        """

        def arg_callable_filter_of_asset_id(arg_iterable_path, arg_node):
            if delimiter_for_key_of_asset not in arg_iterable_path:
                return False
            index_of_asset_id = arg_iterable_path.index(delimiter_for_key_of_asset) + 1
            if len(arg_iterable_path) <= index_of_asset_id:
                return False
            return True

        def arg_callable_formatter_of_asset_id(arg_iterable_path, arg_node):
            if delimiter_for_key_of_asset in arg_iterable_path:
                index_of_asset_id = arg_iterable_path.index(delimiter_for_key_of_asset) + 1
            else:
                index_of_asset_id = 0
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id

        def arg_callable_formatter_of_asset_id_relative_path(arg_iterable_path, arg_node):
            if delimiter_for_key_of_asset not in arg_iterable_path:
                arg_iterable_path.insert(0, delimiter_for_key_of_asset)
            arg_iterable_path.insert(0, node_key)
            index_of_asset_id = arg_iterable_path.index(delimiter_for_key_of_asset) + 1
            arg_iterable_path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            return delimiter_for_path.join(arg_iterable_path_of_asset)

        if immediate:
            # Such as: node_key:.
            _data_tree_node_keys = [node_key, delimiter_for_key_of_asset]
            _data_tree_node_path = delimiter_for_path.join(_data_tree_node_keys)
            _arg_bool_search_sub_tree = False
            _arg_callable_filter = None
        else:
            _data_tree_node_path = node_key
            _arg_bool_search_sub_tree = True
            _arg_callable_filter = arg_callable_filter_of_asset_id

        if only_asset_id:
            _arg_callable_formatter = arg_callable_formatter_of_asset_id
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_id_relative_path

        data_tree_node = self._root.get_node_child_at_path(_data_tree_node_path)
        if data_tree_node is None:
            return []
        paths = self._paths_of_data_tree_node(
            data_tree_node=data_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def get_assets_id_of_node(self, node_key, immediate=False):
        assets_id = self.paths_of_node_assets(node_key, immediate=immediate, only_asset_id=True)
        return set(assets_id)

    def count_assets_of_node(self, node_key, immediate=False):
        """ 统计节点下资产数量 """
        assets_id = self.get_assets_id_of_node(node_key=node_key, immediate=immediate)
        return len(assets_id)


class OrgNodeAssetTree(BaseNodeAssetTree):

    def __init__(self, org_id, *args, **kwargs):
        self._org_id = org_id
        super().__init__(*args, **kwargs)

    @timeit
    def initial(self):
        t1 = time.time()
        with tmp_to_org(self._org_id):
            nodes = list(Node.objects.all().values_list('id', 'key'))
            nodes_id = [str(node_id) for node_id, node_key in nodes]
            nodes_assets_id = Node.assets.through.objects.filter(node_id__in=nodes_id).values_list(
                'node_id', 'asset_id'
            )
            nodes_assets_id_mapping = defaultdict(set)
            for node_id, asset_id in nodes_assets_id:
                nodes_assets_id_mapping[str(node_id)].add(str(asset_id))
        t2 = time.time()

        for node_id, node_key in nodes:
            path_keys_of_node = [node_key, delimiter_for_key_of_asset]
            path_of_node = delimiter_for_path.join(path_keys_of_node)
            data_tree_node = self._append_path_of_data_tree_node(self._root, arg_path=path_of_node)
            for asset_id in nodes_assets_id_mapping[str(node_id)]:
                self._append_path_of_data_tree_node(data_tree_node, arg_path=asset_id)
        t3 = time.time()

        print('t1-t2: {}, t2-t3: {}'.format(t2-t1, t3-t2))


# tree = OrgNodeAssetTree(org_id='')
# tree.initial()
# _nodes_key = tree.get_nodes_key(level=2)
# print(_nodes_key)


class NodeAssetTree(BaseNodeAssetTree):

    def __init__(self, base_tree: OrgNodeAssetTree, nodes, assets, *args, **kwargs):
        self._base_tree = base_tree
        self._nodes = nodes
        self._assets = assets
        super().__init__(*args, **kwargs)

    @timeit
    def initial(self, *args, **kwargs):
        nodes_key = list(self._nodes.values_list('key'))
        for node_key in nodes_key:
            arg_node = self._base_tree.get_node(node_key=node_key)
            arg_node = Data_tree_node(arg_data=arg_node)
            self._append_path_of_data_tree_node(self._root, arg_path=node_key, arg_node=arg_node)

        assets_id = list(self._assets.values_list('id'))
        assets_id_nodes_key = Node.assets.through.objects.filter(asset_id__in=assets_id).values_list(
            'asset_id', 'node__key'
        )
        for asset_id, node_key in assets_id_nodes_key:
            path_keys_of_asset = [node_key, str(asset_id)]
            path_of_asset = delimiter_for_path.join(path_keys_of_asset)
            self._append_path_of_data_tree_node(date_tree_node=self._root, arg_path=path_of_asset)


def get_org_node_asset_tree(org_id):
    org_tree = OrgNodeAssetTree(org_id=org_id)
    org_tree.initial()
    return org_tree


org_id = ''

with tmp_to_org(org_id):
    permission = AssetPermission.objects.get(name='x')

t = get_org_node_asset_tree(org_id=org_id)

node_asset_tree = NodeAssetTree(
    base_tree=t, nodes=permission.nodes.all(), assets=permission.assets.all()
)
node_asset_tree.initial()
_nodes_key = node_asset_tree.get_nodes_key()
print(_nodes_key)
