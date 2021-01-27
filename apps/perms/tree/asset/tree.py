from django.db.models import Q
from perms.models import AssetPermission
from assets.tree.asset import BaseAssetTree, AssetTree, TreeNode


__all__ = ['PermissionAssetTree']


class PermissionAssetTree(BaseAssetTree):
    """ 资产授权树 """

    def __init__(self, asset_tree: AssetTree, permissions, **kwargs):
        self._asset_tree = asset_tree
        self._permissions = permissions
        self._flag_for_immediate_granted = '@'
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
            if self._flag_for_immediate_granted not in arg_iterable_path:
                return False
            if self._flag_for_asset not in arg_iterable_path:
                return False
            return True

        def arg_callable_formatter_of_asset_id_as_path(arg_iterable_path, arg_node):
            index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
            index_of_asset_id = index_of_flag_for_asset + 1
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id

        def arg_callable_formatter_of_asset_path(arg_iterable_path, arg_node):
            index_of_flag_for_asset = arg_iterable_path.index(self._flag_for_asset)
            index_of_asset_id = index_of_flag_for_asset + 1
            path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            path = self._delimiter_for_path.join(path_of_asset)
            return path

        if asset_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_asset_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_path

        _arg_callable_filter = arg_callable_filter_of_immediate_granted_asset

        paths = self._paths_of_tree_node(
            tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_nodes_of_immediate_granted(self):
        """返回直接授权的节点 """

        def arg_callable_filter_of_immediate_granted_node(arg_iterable_path, arg_node):
            if self._flag_for_immediate_granted not in arg_iterable_path:
                return False
            index_of_flag_immediate_granted = arg_iterable_path.index(
                self._flag_for_immediate_granted
            )
            path_of_before_immediate_granted_flag = \
                arg_iterable_path[:index_of_flag_immediate_granted]
            is_node_path = ''.join(path_of_before_immediate_granted_flag).isdigit()
            return is_node_path

        def arg_callable_formatter_of_node_path(arg_iterable_path, arg_node):
            index_of_flag_immediate_granted = arg_iterable_path.index(
                self._flag_for_immediate_granted
            )
            path_of_node = arg_iterable_path[:index_of_flag_immediate_granted]
            return self._delimiter_for_path.join(path_of_node)

        _arg_callable_filter = arg_callable_filter_of_immediate_granted_node
        _arg_callable_formatter = arg_callable_formatter_of_node_path

        paths = self._paths_of_tree_node(
            tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    # 初始化授权资产树

    def initial(self, *args, **kwargs):
        """ 初始化树 """
        permissions_id = self._permissions.values_list('id', flat=True)
        queries = Q(assetpermission_id=permissions_id)
        nodes_key = AssetPermission.nodes.through.objects.filter(queries).values_list(
            'node__key', flat=True
        )
        assets_id = AssetPermission.assets.through.objects.filter(queries).values_list(
            'asset_id', flat=True
        )
        nodes_key = list(set(nodes_key))
        assets_id = list(set([str(asset_id) for asset_id in assets_id]))

        # 添加直接授权的节点以及系统用户
        for node_key in nodes_key:
            # TODO: perf
            # 从 asset_tree 上获取的节点
            tree_node_of_asset_tree = self._asset_tree._get_tree_node_at_path(
                tree_node=self._asset_tree._root, arg_path=node_key
            )
            tree_node_of_granted = TreeNode(arg_data=tree_node_of_asset_tree)
            # 添加授权的节点
            tree_node_of_granted = self._append_path_to_tree_node(
                tree_node=self._root, arg_path=node_key, arg_node=tree_node_of_granted
            )
            # 添加直接授权节点的标志路径
            self._append_path_to_tree_node(
                tree_node=tree_node_of_granted, arg_path=self._flag_for_immediate_granted
            )

        # 添加直接授权的资产
        path_assets = self._asset_tree.paths_of_assets_for_assets_id(assets_id=assets_id)
        for path_asset in path_assets:
            # 添加直接授权的标志路径
            path_asset_of_immediate_granted = self._delimiter_for_path.join([
                path_asset, self._flag_for_immediate_granted
            ])
            self._append_path_to_tree_node(self._root, arg_path=path_asset_of_immediate_granted)
