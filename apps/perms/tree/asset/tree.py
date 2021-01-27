from django.db.models import Q
from perms.models import AssetPermission
from assets.tree.asset import (
    BaseAssetTree,
    AssetTree,
    contains_path_key_for_asset,
    is_node_path,
    iterable_path_as_string,
    arg_callable_formatter_path_for_asset_id_as_path
)


__all__ = ['PermissionAssetTree']


path_key_for_mark_immediate_granted = '@'


def contains_path_key_for_mark_immediate_granted(arg_iterable_path, arg_node):
    """ 路径中是否包含`直接授权的标记` """
    return path_key_for_mark_immediate_granted in arg_iterable_path


def arg_callable_filter_path_for_immediate_granted_asset(arg_iterable_path, arg_node):
    """ 过滤出直接授权的资产的路径 """
    if not contains_path_key_for_mark_immediate_granted(arg_iterable_path, arg_node):
        return False
    if not contains_path_key_for_asset(arg_iterable_path, arg_node):
        return False
    return True


def arg_callable_filter_path_for_immediate_granted_node(arg_iterable_path, arg_node):
    """ 过滤出直接授权的节点的路径 """
    if not contains_path_key_for_mark_immediate_granted(arg_iterable_path, arg_node):
        return False
    index_for_mark = arg_iterable_path.index(path_key_for_mark_immediate_granted)
    path_of_before_mark = arg_iterable_path[:index_for_mark]
    return is_node_path(arg_iterable_path=path_of_before_mark)


def arg_callable_formatter_path_for_immediate_granted_asset(arg_iterable_path, arg_node):
    """ 格式化路径为直接授权的资产的绝对路径 """
    index_for_mark = arg_iterable_path.index(path_key_for_mark_immediate_granted)
    node_path = arg_iterable_path[:index_for_mark]
    return iterable_path_as_string(iterable_path=node_path)


def arg_callable_formatter_path_for_immediate_granted_node(arg_iterable_path, arg_node):
    """ 格式化路径为直接授权的节点的绝对路径 """
    index_for_mark = arg_iterable_path.index(path_key_for_mark_immediate_granted)
    node_path = arg_iterable_path[:index_for_mark]
    return iterable_path_as_string(iterable_path=node_path)


class PermissionAssetTree(BaseAssetTree):
    """ 授权资产树 """

    def __init__(self, asset_tree: AssetTree, permissions, **kwargs):
        self.asset_tree = asset_tree
        self._permissions = permissions
        super().__init__(**kwargs)

    def count_assets_of_granted(self):
        """ 计算所有授权的资产数量 """
        assets_id = self.get_assets_id_of_granted()
        return len(assets_id)

    def count_assets_of_immediate_granted(self):
        """ 计算直接授权的资产数量 """
        assets_id = self.get_assets_id_of_immediate_granted()
        return len(assets_id)

    def count_nodes_of_granted(self):
        """ 获取所有授权的节点数量 """
        nodes_key = self.get_nodes_key_of_granted()
        return len(nodes_key)

    def count_nodes_of_immediate_granted(self):
        """ 计算直接授权的资产数量 """
        nodes_key = self.get_nodes_key_of_immediate_granted()
        return len(nodes_key)

    def get_assets_id_of_granted(self):
        """ 获取所有授权的资产id """
        return self.get_assets_id()

    def get_assets_id_of_immediate_granted(self):
        """ 获取直接授权的资产id """
        assets_id = self.paths_assets_of_immediate_granted(asset_id_as_path=True)
        return list(set(assets_id))

    def get_nodes_key_of_granted(self):
        """ 获取所有授权的节点key """
        immediate_granted_nodes_key = self.get_nodes_key_of_immediate_granted()
        immediate_granted_nodes_children_key = self.get_nodes_children_key(
            nodes_key=immediate_granted_nodes_key
        )
        granted_nodes_key = immediate_granted_nodes_key + immediate_granted_nodes_children_key
        return granted_nodes_key

    def get_nodes_key_of_immediate_granted(self):
        """ 获取直接授权的节点key """
        nodes_key = self.paths_nodes_of_immediate_granted()
        return list(set(nodes_key))

    def paths_assets_of_immediate_granted(self, asset_id_as_path=False):
        """
        return: 返回直接授权的资产
        arg - only_asset_id: 是否只返回资产id
        """

        _arg_callable_filter = arg_callable_filter_path_for_immediate_granted_asset

        if asset_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_path_for_asset_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_path_for_immediate_granted_asset

        paths = self.paths_of_tree_node(
            tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_nodes_of_immediate_granted(self):
        """返回直接授权的节点 """

        _arg_callable_filter = arg_callable_filter_path_for_immediate_granted_node
        _arg_callable_formatter = arg_callable_formatter_path_for_immediate_granted_node

        paths = self.paths_of_tree_node(
            tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def initial(self):
        """ 初始化授权资产树 """
        queries = Q(assetpermission_id__in=self._permissions.values_list('id', flat=True))

        granted_nodes_key = AssetPermission.nodes.through.objects\
            .filter(queries).prefetch_related('node__key').values_list('node__key', flat=True)
        granted_nodes_key = set(granted_nodes_key)

        granted_assets_id = AssetPermission.assets.through.objects\
            .filter(queries).values_list('asset_id', flat=True)
        granted_assets_id = set([str(asset_id) for asset_id in granted_assets_id])

        for node_key in granted_nodes_key:
            self.initial_granted_node(node_path=node_key)

        paths_of_granted_assets = self.asset_tree.paths_assets_of_assets_id(granted_assets_id)
        for asset_path in paths_of_granted_assets:
            self.initial_granted_asset(asset_path=asset_path)

    def initial_granted_node(self, node_path):
        """ 初始化授权的节点 """
        cloned_tree_node = self.asset_tree.clone_tree_node_at_path(arg_path=node_path)
        tree_node = self.append_path_to_tree_node(self._root, node_path, arg_node=cloned_tree_node)
        self.append_path_to_tree_node(tree_node, arg_path=path_key_for_mark_immediate_granted)

    def initial_granted_asset(self, asset_path):
        """
        初始化授权的资产

        Note: 直接添加包含直接授权标志的资产路径, 提升初始化性能
        """
        asset_path = self.iterable_path_as_string([asset_path, path_key_for_mark_immediate_granted])
        self.append_path_to_tree_node(self._root, arg_path=asset_path)
