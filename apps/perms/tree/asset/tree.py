from django.db.models import Q
from perms.models import AssetPermission
from assets.tree.asset import BaseAssetTree, AssetTree, TreeNode
from assets.tree.asset.base import delimiter_for_path, path_key_of_asset


__all__ = ['PermissionAssetTree']


path_key_of_immediate_granted_mark = '@'


class PermissionAssetTree(BaseAssetTree):
    """ 资产授权树 """

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
        nodes_key = []
        nodes_key_of_immediate_granted = self.get_nodes_key_of_immediate_granted()
        nodes_children_key_of_immediate_granted = self.get_nodes_children_key(
            nodes_key=nodes_key_of_immediate_granted
        )
        nodes_key.extend(nodes_key_of_immediate_granted)
        nodes_key.extend(nodes_children_key_of_immediate_granted)
        return list(set(nodes_key))

    def get_nodes_key_of_immediate_granted(self):
        """ 获取直接授权的节点key """
        nodes_key = self.paths_nodes_of_immediate_granted()
        return list(set(nodes_key))

    def paths_assets_of_immediate_granted(self, asset_id_as_path=False):
        """
        return: 返回直接授权的资产
        arg - only_asset_id: 是否只返回资产id
        """

        def arg_callable_filter_of_immediate_granted_asset(arg_iterable_path, arg_node):
            if path_key_of_immediate_granted_mark not in arg_iterable_path:
                return False
            if path_key_of_asset not in arg_iterable_path:
                return False
            return True

        def arg_callable_formatter_of_asset_id_as_path(arg_iterable_path, arg_node):
            index_of_path_key_of_asset = arg_iterable_path.index(path_key_of_asset)
            index_of_asset_id = index_of_path_key_of_asset + 1
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id

        def arg_callable_formatter_of_asset_path(arg_iterable_path, arg_node):
            index_of_path_key_of_asset = arg_iterable_path.index(path_key_of_asset)
            index_of_asset_id = index_of_path_key_of_asset + 1
            path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            path = delimiter_for_path.join(path_of_asset)
            return path

        if asset_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_asset_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_path

        _arg_callable_filter = arg_callable_filter_of_immediate_granted_asset

        paths = self.paths_of_tree_node(
            tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_nodes_of_immediate_granted(self):
        """返回直接授权的节点 """

        def arg_callable_filter_of_immediate_granted_node(arg_iterable_path, arg_node):
            if path_key_of_immediate_granted_mark not in arg_iterable_path:
                return False
            index_of_flag_immediate_granted = arg_iterable_path.index(
                path_key_of_immediate_granted_mark
            )
            path_of_before_immediate_granted_flag = \
                arg_iterable_path[:index_of_flag_immediate_granted]
            is_node_path = ''.join(path_of_before_immediate_granted_flag).isdigit()
            return is_node_path

        def arg_callable_formatter_of_node_path(arg_iterable_path, arg_node):
            index_of_flag_immediate_granted = arg_iterable_path.index(
                path_key_of_immediate_granted_mark
            )
            path_of_node = arg_iterable_path[:index_of_flag_immediate_granted]
            return delimiter_for_path.join(path_of_node)

        _arg_callable_filter = arg_callable_filter_of_immediate_granted_node
        _arg_callable_formatter = arg_callable_formatter_of_node_path

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
        self.append_path_to_tree_node(tree_node, arg_path=path_key_of_immediate_granted_mark)

    def initial_granted_asset(self, asset_path):
        """
        初始化授权的资产

        Note: 直接添加包含直接授权标志的资产路径, 提升初始化性能
        """
        asset_path = self.iterable_path_as_string([asset_path, path_key_of_immediate_granted_mark])
        self.append_path_to_tree_node(self._root, arg_path=asset_path)
