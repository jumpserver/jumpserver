import abc
from data_tree import Data_tree_node


__all__ = ['TreeNode', 'BaseAssetTree']


class TreeNode(Data_tree_node):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class BaseAssetTree(object):
    """ 基本的资产节点树 """
    def __init__(self, **kwargs):
        self._delimiter_for_path = ':'
        self._flag_for_asset = '.'
        self._root = TreeNode(arg_string_delimiter_for_path=self._delimiter_for_path)

    @abc.abstractmethod
    def initial(self):
        """ 初始化树 """
        raise NotImplemented

    @staticmethod
    def _append_path_to_tree_node(tree_node, arg_path, arg_node=None) -> TreeNode:
        """
        添加路径到 tree_node
        arg - tree_node: instance of TreeNode
        arg - arg_path: str
        arg - arg_node: None or instance of TreeNode
        """
        tree_node_at_path = tree_node.append_path(arg_path=arg_path, arg_node=arg_node)
        return tree_node_at_path

    @staticmethod
    def _get_tree_node_at_path(tree_node: TreeNode, arg_path) -> TreeNode:
        """ 根据路径获取 tree_node """
        tree_node_at_path = tree_node.get_node_child_at_path(arg_path=arg_path)
        return tree_node_at_path

    @staticmethod
    def _get_tree_node_parent(tree_node: TreeNode) -> TreeNode:
        """ 获取 tree_node 的父节点 """
        return tree_node.get_node_parent()

    @staticmethod
    def _paths_of_tree_node(tree_node: TreeNode, **kwargs) -> list:
        """ 获取 tree_node 节点下的路径 """
        _arg_bool_search_sub_tree = kwargs.get('arg_bool_search_sub_tree', True)
        _arg_bool_search_entire_tree = kwargs.get('arg_bool_search_entire_tree', False)
        _arg_callable_filter = kwargs.get('arg_callable_filter')
        _arg_callable_formatter = kwargs.get('arg_callable_formatter')

        paths = tree_node.get_list_of_pairs_paths_and_node_children(
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_bool_search_entire_tree=_arg_bool_search_entire_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    @staticmethod
    def compute_ancestor_node_key(node_key):
        """ 计算 node 的祖先节点 key """
        ancestor_key = []
        while len(node_key) > 1:
            parent_key = node_key.rsplit(sep=':', maxsplit=1)[0]
            ancestor_key.insert(0, parent_key)
            node_key = parent_key
        return ancestor_key

    def count_assets(self):
        """ 计算所有的资产数量 """
        assets_id = self.get_assets_id()
        return len(assets_id)

    def count_assets_of_node(self, node_key, immediate=False):
        """
        计算节点下的资产数量

        arg - node_key:
        arg - immediate: if True: 只计算节点的直接资产; else: 计算节点下的所有资产;
        """
        assets_id = self.get_assets_id_of_node(node_key=node_key, immediate=immediate)
        return len(set(assets_id))

    def count_nodes(self, level=None):
        """ 计算所有节点的数量 """
        nodes_key = self.get_nodes_key(level=level)
        return len(nodes_key)

    def count_node_children(self, node_key, level=None):
        node_children_key = self.get_node_children_key(node_key=node_key, level=level)
        return len(node_children_key)

    def get_assets_id(self):
        """ 获取所有资产id """
        assets_id = self.paths_of_assets(asset_id_as_path=True)
        return list(set(assets_id))

    def get_assets_id_of_node(self, node_key, immediate=False):
        """ 获取节点下的资产id """
        assets_id = self.paths_of_assets_for_node(
            node_key=node_key, immediate=immediate, asset_id_as_path=True
        )
        return list(set(assets_id))

    def get_nodes_key(self, level=None):
        nodes_key = self.paths_of_nodes(level=level)
        return nodes_key

    def get_nodes_key_for_asset(self, asset_id):
        nodes_key_of_asset = self.paths_of_assets_for_assets_id(
            assets_id=[asset_id], asset_node_key_as_path=True
        )
        return nodes_key_of_asset

    def get_nodes_children_key(self, nodes_key):
        nodes_children_key = set()
        for node_key in nodes_key:
            node_children_key = self.get_node_children_key(node_key=node_key)
            nodes_children_key.update(node_children_key)
        return list(nodes_children_key)

    def get_node_children_key(self, node_key, level=None):
        """ 获取子孙节点的key """
        node_children_key = self.paths_of_node_children(node_key=node_key, level=level)
        return node_children_key

    def paths_of_nodes(self, level=None):
        """ 获取所有 nodes 的路径 """
        return self.paths_of_node_children(node_key=None, level=level)

    def paths_of_node_children(self, node_key=None, level=None):
        """
        return: 返回节点的子节点的路径
        arg: node_key - 节点key
        arg: immediate - 是否是直接子节点
        """

        def arg_callable_filter_of_node_key(arg_iterable_path, arg_node):
            is_node_path = ''.join(arg_iterable_path).isdigit()
            return is_node_path

        def arg_callable_filter_of_node_key_level(arg_iterable_path, arg_node):
            if not arg_callable_filter_of_node_key(arg_iterable_path, arg_node):
                return False
            return level >= len(arg_iterable_path)

        def arg_callable_formatter_of_node_path(arg_iterable_path, arg_node):
            return self._delimiter_for_path.join(arg_iterable_path)

        def arg_callable_formatter_of_node_absolute_path(arg_iterable_path, arg_node):
            arg_iterable_path.insert(0, node_key)
            return self._delimiter_for_path.join(arg_iterable_path)

        if node_key is None:
            _tree_node = self._root
            _arg_callable_formatter = arg_callable_formatter_of_node_path
        else:
            _tree_node = self._get_tree_node_at_path(
                tree_node=self._root, arg_path=node_key
            )
            if _tree_node is None:
                return []
            _arg_callable_formatter = arg_callable_formatter_of_node_absolute_path

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

        paths = self._paths_of_tree_node(
            tree_node=_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_assets(self, asset_id_as_path=False):
        """ 所有资产的路径 """
        paths_of_assets = self.paths_of_assets_for_node(asset_id_as_path=asset_id_as_path)
        return paths_of_assets

    def paths_of_assets_for_node(self, node_key=None, immediate=False, asset_id_as_path=False):
        """
        return: 返回节点下的资产的路径
        arg: node_key - 节点 key
        arg: immediate - 是否是直接资产
        arg: only_asset_id - 是否只返回资产id
        """

        def arg_callable_filter_of_asset(arg_iterable_path, arg_node):
            if self._flag_for_asset not in arg_iterable_path:
                return False
            index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
            index_of_asset_id = index_of_flag_for_asset + 1
            return len(arg_iterable_path) == index_of_asset_id + 1

        def arg_callable_formatter_of_asset_id_as_path(arg_iterable_path, arg_node):
            if self._flag_for_asset in arg_iterable_path:
                index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
                index_of_asset_id = index_of_flag_for_asset + 1
            else:
                index_of_asset_id = 0
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id

        def arg_callable_formatter_of_asset_absolute_path(arg_iterable_path, arg_node):
            # TODO: Perf
            if node_key is None:
                return self._delimiter_for_path.join(arg_iterable_path)

            if self._flag_for_asset not in arg_iterable_path:
                arg_iterable_path.insert(0, self._flag_for_asset)

            arg_iterable_path.insert(0, node_key)

            index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
            index_of_asset_id = index_of_flag_for_asset + 1
            path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            path = self._delimiter_for_path.join(path_of_asset)
            return path

        if node_key is None:
            _tree_node = self._root
            _arg_bool_search_sub_tree = True
            _arg_callable_filter = arg_callable_filter_of_asset
        else:
            if immediate:
                # Such as: node_key:.
                _tree_node_keys = [node_key, self._flag_for_asset]
                _tree_node_path = self._delimiter_for_path.join(_tree_node_keys)
                _arg_bool_search_sub_tree = False
                _arg_callable_filter = None
            else:
                _tree_node_path = node_key
                _arg_bool_search_sub_tree = True
                _arg_callable_filter = arg_callable_filter_of_asset

            _tree_node = self._get_tree_node_at_path(
                tree_node=self._root, arg_path=_tree_node_path
            )
            if _tree_node is None:
                return []

        if asset_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_asset_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_absolute_path

        paths = self._paths_of_tree_node(
            tree_node=_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_assets_for_assets_id(self, assets_id, asset_node_key_as_path=False):
        """ 获取多个资产的所有路径 """

        def arg_callable_filter_of_in_assets_id(arg_iterable_path, arg_node):
            if self._flag_for_asset not in arg_iterable_path:
                return False
            index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
            index_of_asset_id = index_of_flag_for_asset + 1
            if len(arg_iterable_path) != index_of_asset_id + 1:
                return False
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id in assets_id

        def arg_callable_formatter_of_asset_path(arg_iterable_path, arg_node):
            index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
            index_of_asset_id = index_of_flag_for_asset + 1
            path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            path = self._delimiter_for_path.join(path_of_asset)
            return path

        def arg_callable_formatter_of_asset_node_as_path(arg_iterable_path, arg_node):
            index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
            path_of_node = arg_iterable_path[:index_of_flag_for_asset]
            path = self._delimiter_for_path.join(path_of_node)
            return path

        if asset_node_key_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_asset_node_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_path

        _arg_callable_filter = arg_callable_filter_of_in_assets_id

        paths = self._paths_of_tree_node(
            tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

