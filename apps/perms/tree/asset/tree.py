from collections import defaultdict
from django.db.models import Q
from users.models import User
from django.core.cache import cache
from perms.models import AssetPermission
from perms.utils.asset import get_user_all_assetpermissions_id
from assets.tree.asset import (
    BaseAssetTree,
    AssetTree,
    AssetTreeManager,
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

    def __init__(self, user: User, **kwargs):
        self._user = user
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
        permissions_id = get_user_all_assetpermissions_id(user=self._user)

        queries = Q(assetpermission_id__in=permissions_id)

        granted_nodes = AssetPermission.nodes.through.objects\
            .filter(queries)\
            .prefetch_related('node__key', 'node__org_id')\
            .values_list('node__org_id', 'node__key')
        granted_nodes = set(granted_nodes)

        granted_assets = AssetPermission.assets.through.objects\
            .prefetch_related('asset__org_id')\
            .filter(queries)\
            .values_list('asset_id', 'asset__org_id')
        granted_assets = set([str(asset_id) for asset_id in granted_assets])

        org_id_nodes_key_mapping = defaultdict(set)
        for node__org_id, node_key in granted_nodes:
            org_id_nodes_key_mapping[str(node__org_id)].add(node_key)

        org_id_assets_id_mapping = defaultdict(set)
        for asset__org_id, asset_id in granted_assets:
            org_id_assets_id_mapping[str(asset__org_id)].add(str(asset_id))

        org_id_nodes_key_assets_id_mapping = defaultdict(dict)
        for org_id, nodes_key in org_id_nodes_key_mapping.items():
            org_id_nodes_key_assets_id_mapping[org_id]['nodes_key'] = nodes_key

        for org_id, assets_id in org_id_assets_id_mapping.items():
            org_id_nodes_key_assets_id_mapping[org_id]['assets_id'] = assets_id

        for org_id, nodes_key_assets_id in org_id_nodes_key_assets_id_mapping.items():
            org_asset_tree = self.__get_asset_tree_of_org(org_id=org_id)
            nodes_key = nodes_key_assets_id['nodes_key']
            assets_id = nodes_key_assets_id['assets_id']
            self.initial_granted_nodes(asset_tree=org_asset_tree, nodes_key=nodes_key)
            self.initial_granted_assets(asset_tree=org_asset_tree, assets_id=assets_id)

    def initial_granted_nodes(self, asset_tree: AssetTree, nodes_key):
        """ 初始化授权的节点 """
        for node_key in nodes_key:
            cloned_tree_node = asset_tree.clone_tree_node_at_path(arg_path=node_key)
            tree_node = self.append_path_to_tree_node(
                tree_node=self._root, arg_path=node_key, arg_node=cloned_tree_node
            )
            self.append_path_to_tree_node(tree_node, arg_path=path_key_for_mark_immediate_granted)

    def initial_granted_assets(self, asset_tree: AssetTree, assets_id):
        """
        初始化授权的资产

        Note: 直接添加包含直接授权标志的资产路径, 提升初始化性能
        """
        paths_of_granted_assets = asset_tree.paths_assets_of_assets_id(assets_id)
        for asset_path in paths_of_granted_assets:
            asset_path = self.iterable_path_as_string([
                asset_path, path_key_for_mark_immediate_granted
            ])
            self.append_path_to_tree_node(self._root, arg_path=asset_path)

    @staticmethod
    def __get_asset_tree_of_org(org_id) -> AssetTree:
        asset_tree_manager = AssetTreeManager()
        return asset_tree_manager.get_tree(org_id=org_id)
