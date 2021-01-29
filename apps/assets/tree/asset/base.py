import abc
from data_tree import Data_tree_node


__all__ = [
    'delimiter_for_path',
    'path_key_for_asset',
    'contains_path_key_for_asset',
    'is_node_path',
    'iterable_path_as_string',
    'arg_callable_filter_path_for_node',
    'arg_callable_filter_path_for_asset',
    'arg_callable_formatter_path_for_path_as_string',
    'arg_callable_formatter_path_for_path_as_iterable',
    'arg_callable_formatter_path_for_asset_id_as_path',
    'TreeNode',
    'BaseAssetTree'
]


delimiter_for_path = ':'
path_key_for_asset = '.'


def contains_path_key_for_asset(arg_iterable_path, arg_node):
    """ 路径中是否包含`标示资产的路径key` """
    return path_key_for_asset in arg_iterable_path


def is_node_path(arg_iterable_path):
    """ 是否是节点路径 """
    return ''.join(arg_iterable_path).isdigit()


def iterable_path_as_string(iterable_path):
    """ 可迭代路径转化为string """
    return delimiter_for_path.join(iterable_path)


def arg_callable_filter_path_for_node(arg_iterable_path, arg_node):
    """ 过滤出节点的路径 """
    return is_node_path(arg_iterable_path=arg_iterable_path)


def arg_callable_filter_path_for_asset(arg_iterable_path, arg_node):
    """ 过滤出资产的路径 """
    if not contains_path_key_for_asset(arg_iterable_path, arg_node):
        return False
    index_for_path_key_for_asset = arg_iterable_path.index(path_key_for_asset)
    index_for_asset_id = index_for_path_key_for_asset + 1
    return len(arg_iterable_path) == index_for_asset_id + 1


def arg_callable_formatter_path_for_path_as_string(arg_iterable_path, arg_node):
    """ 格式化为字符串路径 """
    return iterable_path_as_string(iterable_path=arg_iterable_path)


def arg_callable_formatter_path_for_path_as_iterable(arg_iterable_path, arg_node):
    """ 格式化为可迭代路径 """
    return arg_iterable_path


def arg_callable_formatter_path_for_asset_id_as_path(arg_iterable_path, arg_node):
    """ 资产ID作为路径的格式化器 """
    index_for_path_key_for_asset = arg_iterable_path.index(path_key_for_asset)
    index_for_asset_id = index_for_path_key_for_asset + 1
    return arg_iterable_path[index_for_asset_id]


class TreeNode(Data_tree_node):
    """ 树节点 """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class BaseAssetTree(object):
    """ 基本的资产树 """
    def __init__(self, **kwargs):
        self._root = TreeNode(arg_string_delimiter_for_path=delimiter_for_path)

    @abc.abstractmethod
    def initial(self):
        """ 初始化树 """
        raise NotImplemented

    @staticmethod
    def append_path_to_tree_node(tree_node, arg_path, arg_node=None) -> TreeNode:
        """
        添加路径到 tree_node
        arg - tree_node: instance of TreeNode
        arg - arg_path: str
        arg - arg_node: None or instance of TreeNode
        """
        _tree_node = tree_node.append_path(arg_path=arg_path, arg_node=arg_node)
        return _tree_node

    def clone_tree_node_at_path(self, arg_path) -> TreeNode:
        _tree_node = self.get_tree_node_at_path(arg_path=arg_path)
        _cloned_tree_node = self.clone_tree_node(tree_node=_tree_node)
        return _cloned_tree_node

    @staticmethod
    def clone_tree_node(tree_node: TreeNode) -> TreeNode:
        if isinstance(tree_node, TreeNode):
            _tree_node = TreeNode(arg_data=tree_node)
        else:
            _tree_node = None
        return _tree_node

    def get_tree_node_at_path(self, arg_path) -> TreeNode:
        """ 根据路径获取 tree_node """
        _tree_node = self._root.get_node_child_at_path(arg_path=arg_path)
        return _tree_node

    # def get_object_at_path(self, arg_path):
    #     return self._root.get_object_at_path(arg_path=arg_path, arg_bool_path_is_absolute=True)

    # @staticmethod
    # def set_node_object_to_tree_node(tree_node: TreeNode, node):
    #     return tree_node.set_object_stored_in_node(
    #         arg_path=None, arg_object=node, arg_bool_path_is_absolute=False
    #     )

    # @staticmethod
    # def set_asset_object_to_tree_node(tree_node: TreeNode, asset):
    #     return tree_node.set_object_stored_in_node(
    #         arg_path=None, arg_object=asset, arg_bool_path_is_absolute=False
    #     )

    def count_assets(self):
        """ 计算所有的资产数量 """
        assets_id = self.get_assets_id()
        return len(assets_id)

    def count_assets_of_node(self, node_key, immediate=False):
        """ 计算节点下的资产数量 """
        # node = self.get_node(node_key=node_key)
        # if hasattr(node, 'count_of_assets'):
        #     return getattr(node, 'count_of_assets')
        assets_id = self.get_assets_id_of_node(node_key=node_key, immediate=immediate)
        count_assets = len(set(assets_id))
        # setattr(node, 'count_of_assets', count_assets)
        return count_assets

    def count_nodes(self, level=None):
        """ 计算所有节点的数量 """
        nodes_key = self.get_nodes_key(level=level)
        return len(nodes_key)

    def count_node_children(self, node_key, level=None):
        node_children_key = self.get_node_children_key(node_key=node_key, level=level)
        return len(node_children_key)

    def get_assets_id(self):
        """ 获取所有资产id """
        assets_id = self.paths_assets(asset_id_as_path=True)
        return list(set(assets_id))

    def get_assets_id_of_node(self, node_key, immediate=False):
        """ 获取节点下的资产id """
        assets_id = self.paths_assets_of_node(node_key, immediate=immediate, asset_id_as_path=True)
        return list(set(assets_id))

    # def get_nodes(self, level=None):
    #     nodes_key = self.get_nodes_key(level=level)
    #     nodes = [self.get_node(node_key=node_key) for node_key in nodes_key]
    #     return nodes

    # def get_asset(self, asset_path):
    #     return self.get_object_at_path(arg_path=asset_path)

    # def get_node(self, node_key):
    #     return self.get_object_at_path(arg_path=node_key)

    def get_nodes_key(self, level=None):
        """ 获取所有节点的key """
        nodes_key = self.paths_nodes(level=level)
        return nodes_key

    def get_nodes_children_key(self, nodes_key):
        """ 获取节点子孙节点的key """
        nodes_children_key = set()
        for node_key in nodes_key:
            node_children_key = self.get_node_children_key(node_key=node_key)
            nodes_children_key.update(node_children_key)
        return list(nodes_children_key)

    def get_node_children_key(self, node_key, level=None):
        """ 获取子孙节点的key """
        node_children_key = self.paths_node_children(node_key=node_key, level=level)
        return node_children_key

    def paths_nodes(self, level=None):
        """ 获取所有 nodes 的路径 """
        return self.paths_node_children(node_key=None, level=level)

    def paths_node_children(self, node_key=None, level=None):
        """
        return: 返回节点的子节点的路径
        arg: node_key - 节点key
        """

        assert level is None or isinstance(level, int), '`level` should be of type int or None'

        if level == 0:
            return []

        if level == 1:
            _arg_bool_search_sub_tree = False
        else:
            _arg_bool_search_sub_tree = True

        if node_key is None:
            _tree_node = self._root
        else:
            _tree_node = self.get_tree_node_at_path(arg_path=node_key)

        if _tree_node is None:
            return []

        _arg_callable_filter = arg_callable_filter_path_for_node
        _arg_callable_formatter = arg_callable_formatter_path_for_path_as_iterable

        paths = self.paths_of_tree_node(
            tree_node=_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )

        if level is None:
            _to_filter_level = False
        else:
            _to_filter_level = True

        if _to_filter_level:
            paths = [path for path in paths if len(path) <= level]

        if _tree_node is self._root:
            _is_absolute_path = True
        else:
            _is_absolute_path = False

        if _is_absolute_path:
            paths = [self.iterable_path_as_string(path) for path in paths]
        else:
            paths = [self.iterable_path_as_string([node_key, path]) for path in paths]

        return paths

    def paths_assets(self, asset_id_as_path=False):
        """ 所有资产的路径 """
        return self.paths_assets_of_node(node_key=None, asset_id_as_path=asset_id_as_path)

    def paths_assets_of_node(self, node_key=None, immediate=False, asset_id_as_path=False):
        """
        return: 返回节点下所有资产的路径
        arg: node_key - 节点 key
        arg: only_asset_id - 是否只返回资产id
        """

        if immediate:
            return self.paths_assets_of_node_immediate(node_key, asset_id_as_path=asset_id_as_path)

        if node_key is None:
            _tree_node = self._root
        else:
            _tree_node = self.get_tree_node_at_path(arg_path=node_key)

        if _tree_node is None:
            return []

        if asset_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_path_for_asset_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_path_for_path_as_string

        _arg_bool_search_sub_tree = True
        _arg_callable_filter = arg_callable_filter_path_for_asset

        paths = self.paths_of_tree_node(
            tree_node=_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )

        if asset_id_as_path:
            _to_absolute_path = False
        else:
            _to_absolute_path = True

        if _tree_node is self._root:
            _is_absolute_path = True
        else:
            _is_absolute_path = False

        if _to_absolute_path and not _is_absolute_path:
            paths = [iterable_path_as_string([node_key, path]) for path in paths]

        return paths

    def paths_assets_of_node_immediate(self, node_key=None, asset_id_as_path=False):
        """ 获取节点下直接资产的路径 """
        if node_key is None:
            _tree_nodes_paths = self.paths_nodes(level=1)
        else:
            _tree_nodes_paths = [node_key]

        paths = []

        _tree_node_paths = [
            iterable_path_as_string([_tree_node_path, path_key_for_asset])
            for _tree_node_path in _tree_nodes_paths
        ]

        for _tree_node_path in _tree_node_paths:
            _tree_node = self.get_tree_node_at_path(arg_path=_tree_node_path)
            _assets_id = self.paths_of_tree_node(tree_node=_tree_node)
            if asset_id_as_path:
                paths.extend(_assets_id)
                continue

            assets_paths = [
                iterable_path_as_string([_tree_node_path, _asset_id]) for _asset_id in _assets_id
            ]
            paths.extend(assets_paths)

        return paths

    def paths_assets_of_assets_id(self, assets_id):
        """ 获取多个资产的所有路径 """

        _arg_callable_filter = arg_callable_filter_path_for_asset
        _arg_callable_formatter = arg_callable_formatter_path_for_path_as_iterable

        paths_assets = self.paths_of_tree_node(
            tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        paths_assets = [asset_path for asset_path in paths_assets if asset_path[-1] in assets_id]
        paths = [self.iterable_path_as_string(iterable_path=path) for path in paths_assets]
        return paths

    @staticmethod
    def paths_of_tree_node(tree_node: TreeNode, **kwargs) -> list:
        """ 获取 tree_node 节点下的路径 """
        _default_arg_callable_formatter = arg_callable_formatter_path_for_path_as_string

        _arg_bool_search_sub_tree = kwargs.get('arg_bool_search_sub_tree', True)
        _arg_callable_filter = kwargs.get('arg_callable_filter')
        _arg_callable_formatter = kwargs.get('arg_callable_formatter')
        _arg_callable_formatter = _arg_callable_formatter or _default_arg_callable_formatter

        paths = tree_node.get_list_of_pairs_paths_and_node_children(
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    @staticmethod
    def iterable_path_as_string(iterable_path):
        """ 可迭代路径转化为string """
        return delimiter_for_path.join(iterable_path)
