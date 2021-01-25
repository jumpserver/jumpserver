import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", 'jumpserver.settings')
django.setup()

import abc
import time
from data_tree import Data_tree_node
from assets.models import Asset, Node
from perms.models import AssetPermission
from common.utils import lazyproperty, timeit
from collections import defaultdict
from orgs.utils import tmp_to_org
from django.db.models import Q

delimiter_for_path = ':'
delimiter_for_key_of_asset = '.'


class BaseTree(object):
    """ 基本的资产节点树 """
    def __init__(self, org_id, *args, **kwargs):
        self._root = Data_tree_node(arg_string_delimiter_for_path=delimiter_for_path)
        self._org_id = org_id
        self.initial()

    @abc.abstractmethod
    def initial(self):
        """ 初始化树 """
        raise NotImplemented

    @staticmethod
    def _append_path_to_data_tree_node(data_tree_node, arg_path, **kwargs) -> Data_tree_node:
        """ 给 Data_tree_node 节点添加路径 """
        assert isinstance(data_tree_node, Data_tree_node), (
            '`data_tree_node` must be an instance of `Data_tree_node`'
        )
        arg_node = kwargs.get('arg_node')
        data_tree_node_of_path = data_tree_node.append_path(arg_path=arg_path, arg_node=arg_node)
        return data_tree_node_of_path

    def _get_data_tree_node_at_path(self, arg_path) -> Data_tree_node:
        """ 获取 Data_tree_node 根据路径"""
        data_tree_node = self._root.get_node_child_at_path(arg_path=arg_path)
        return data_tree_node

    @staticmethod
    def _paths_of_data_tree_node(data_tree_node: Data_tree_node, **kwargs) -> list:
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

    @staticmethod
    def compute_ancestor_node_key(node_key):
        ancestor_key = []
        while len(node_key) > 1:
            parent_key = node_key.rsplit(sep=delimiter_for_path, maxsplit=1)[0]
            ancestor_key.insert(0, parent_key)
            node_key = parent_key
        return ancestor_key

    def count_assets(self):
        assets_id = self.get_assets_id()
        return len(assets_id)

    def count_assets_of_node(self, node_key, immediate=False):
        """ 计算节点下资产数量 """
        assets_id = self.get_assets_id_of_node(node_key=node_key, immediate=immediate)
        return len(set(assets_id))

    def count_nodes(self, level=None):
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
            nodes_children_key.add(node_children_key)
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
            return delimiter_for_path.join(arg_iterable_path)

        def arg_callable_formatter_of_node_absolute_path(arg_iterable_path, arg_node):
            arg_iterable_path.insert(0, node_key)
            return delimiter_for_path.join(arg_iterable_path)

        if node_key is None:
            _data_tree_node = self._root
            _arg_callable_formatter = arg_callable_formatter_of_node_path
        else:
            _data_tree_node = self._get_data_tree_node_at_path(arg_path=node_key)
            if _data_tree_node is None:
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

        paths = self._paths_of_data_tree_node(
            data_tree_node=_data_tree_node,
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
            if delimiter_for_key_of_asset not in arg_iterable_path:
                return False
            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            index_of_asset_id = index_of_delimiter_for_asset + 1
            return len(arg_iterable_path) == index_of_asset_id + 1

        def arg_callable_formatter_of_asset_id_as_path(arg_iterable_path, arg_node):
            if delimiter_for_key_of_asset in arg_iterable_path:
                index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
                index_of_asset_id = index_of_delimiter_for_asset + 1
            else:
                index_of_asset_id = 0
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id

        def arg_callable_formatter_of_asset_absolute_path(arg_iterable_path, arg_node):
            if delimiter_for_key_of_asset not in arg_iterable_path:
                arg_iterable_path.insert(0, delimiter_for_key_of_asset)

            arg_iterable_path.insert(0, node_key)

            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            index_of_asset_id = index_of_delimiter_for_asset + 1
            path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            path = delimiter_for_path.join(path_of_asset)
            return path

        if node_key is None:
            _data_tree_node = self._root
            _arg_bool_search_sub_tree = True
            _arg_callable_filter = arg_callable_filter_of_asset
        else:
            if immediate:
                # Such as: node_key:.
                _data_tree_node_keys = [node_key, delimiter_for_key_of_asset]
                _data_tree_node_path = delimiter_for_path.join(_data_tree_node_keys)
                _arg_bool_search_sub_tree = False
                _arg_callable_filter = None
            else:
                _data_tree_node_path = node_key
                _arg_bool_search_sub_tree = True
                _arg_callable_filter = arg_callable_filter_of_asset

            _data_tree_node = self._get_data_tree_node_at_path(arg_path=_data_tree_node_path)
            if _data_tree_node is None:
                return []

        if asset_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_asset_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_absolute_path

        paths = self._paths_of_data_tree_node(
            data_tree_node=_data_tree_node,
            arg_bool_search_sub_tree=_arg_bool_search_sub_tree,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_assets_for_assets_id(self, assets_id, asset_node_key_as_path=False):
        """ 获取多个资产的所有路径 """

        def arg_callable_filter_of_in_assets_id(arg_iterable_path, arg_node):
            if delimiter_for_key_of_asset not in arg_iterable_path:
                return False
            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            index_of_asset_id = index_of_delimiter_for_asset + 1
            if len(arg_iterable_path) != index_of_asset_id + 1:
                return False
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id in assets_id

        def arg_callable_formatter_of_asset_path(arg_iterable_path, arg_node):
            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            index_of_asset_id = index_of_delimiter_for_asset + 1
            path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            path = delimiter_for_path.join(path_of_asset)
            return path

        def arg_callable_formatter_of_asset_node_as_path(arg_iterable_path, arg_node):
            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            path_of_node = arg_iterable_path[:index_of_delimiter_for_asset]
            path = delimiter_for_path.join(path_of_node)
            return path

        if asset_node_key_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_asset_node_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_path

        _arg_callable_filter = arg_callable_filter_of_in_assets_id

        paths = self._paths_of_data_tree_node(
            data_tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths


class AssetTree(BaseTree):
    """ 资产树 """

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
            path_of_node = delimiter_for_path.join([node_key, delimiter_for_key_of_asset])
            data_tree_node = self._append_path_to_data_tree_node(self._root, arg_path=path_of_node)
            for asset_id in nodes_assets_id_mapping[str(node_id)]:
                self._append_path_to_data_tree_node(data_tree_node, arg_path=asset_id)

        t3 = time.time()

        print('t1-t2: {}, t2-t3: {}'.format(t2-t1, t3-t2))


asset_tree = AssetTree(org_id='')


delimiter_for_key_of_system_user = '$'
delimiter_for_key_of_immediate_granted_flag = '@'


class AssetPermissionTree(BaseTree):
    """ 资产授权树 """

    def __init__(self, permissions, *args, **kwargs):
        self._permissions = permissions
        super().__init__(*args, **kwargs)

    @property
    def asset_tree(self) -> AssetTree:
        return asset_tree

    def initial(self, *args, **kwargs):
        """ 初始化树 """
        permissions_id = self._permissions.values_list('id', flat=True)
        for permission_id in permissions_id:
            self.initial_of_permission_id(permission_id=permission_id)

    def initial_of_permission_id(self, permission_id):
        """ 根据单个授权规则初始化树 """
        queries = Q(assetpermission_id=permission_id)
        nodes_key = AssetPermission.nodes.through.objects.filter(queries).values_list(
            'node__key', flat=True
        )
        assets_id = AssetPermission.assets.through.objects.filter(queries).values_list(
            'asset_id', flat=True
        )
        assets_id = [str(asset_id) for asset_id in assets_id]
        system_users_id = AssetPermission.system_users.through.objects.filter(queries).values_list(
            'systemuser_id', flat=True
        )
        system_users_id = [str(system_user_id) for system_user_id in system_users_id]

        # 添加直接授权的节点以及系统用户
        for node_key in nodes_key:
            # 获取直接授权节点的标志
            path_of_immediate_granted_node_flag = delimiter_for_path.join([
                node_key, delimiter_for_key_of_immediate_granted_flag
            ])
            data_tree_node_of_immediate_granted_node_flag = self._get_data_tree_node_at_path(
                arg_path=path_of_immediate_granted_node_flag
            )
            if data_tree_node_of_immediate_granted_node_flag is None:
                # 添加授权的节点
                arg_node = self.asset_tree._get_data_tree_node_at_path(arg_path=node_key)
                arg_node = Data_tree_node(arg_data=arg_node)
                data_tree_node = self._append_path_to_data_tree_node(
                    data_tree_node=self._root, arg_path=node_key, arg_node=arg_node
                )

                # 添加直接授权的标志路径
                self._append_path_to_data_tree_node(
                    data_tree_node=data_tree_node,
                    arg_path=delimiter_for_key_of_immediate_granted_flag
                )

                # 添加授权的系统用户容器路径
                data_tree_node_of_system_users = self._append_path_to_data_tree_node(
                    data_tree_node=data_tree_node, arg_path=delimiter_for_key_of_system_user
                )
            else:
                # 之前的授权规则已经添加过
                data_tree_node: Data_tree_node = \
                    data_tree_node_of_immediate_granted_node_flag.get_node_parent()
                data_tree_node_of_system_users = data_tree_node.get_node_child_at_path(
                    arg_path=delimiter_for_key_of_system_user
                )

            # 添加授权的系统用户
            for system_user_id in system_users_id:
                self._append_path_to_data_tree_node(
                    data_tree_node=data_tree_node_of_system_users, arg_path=system_user_id
                )

        # 添加直接授权的资产以及系统用户
        path_of_assets = self.asset_tree.paths_of_assets_for_assets_id(assets_id=assets_id)
        for path_of_asset in path_of_assets:
            path_of_immediate_granted_asset_flag = delimiter_for_path.join([
                path_of_asset, delimiter_for_key_of_immediate_granted_flag
            ])
            data_tree_node_of_immediate_granted_asset_flag = self._get_data_tree_node_at_path(
                arg_path=path_of_immediate_granted_asset_flag
            )
            if data_tree_node_of_immediate_granted_asset_flag is None:
                # 添加授权的资产
                data_tree_node_of_asset = self._append_path_to_data_tree_node(
                    data_tree_node=self._root, arg_path=path_of_asset
                )
                # 添加直接授权的标志路径
                self._append_path_to_data_tree_node(
                    data_tree_node=data_tree_node_of_asset,
                    arg_path=delimiter_for_key_of_immediate_granted_flag
                )
                # 添加授权的系统用户容器路径
                data_tree_node_of_asset_system_users = self._append_path_to_data_tree_node(
                    data_tree_node=data_tree_node_of_asset,
                    arg_path=delimiter_for_key_of_system_user
                )
            else:
                # 之前的授权规则已经添加过
                data_tree_node_of_asset: Data_tree_node = \
                    data_tree_node_of_immediate_granted_asset_flag.get_node_parent()
                data_tree_node_of_asset_system_users = \
                    data_tree_node_of_asset.get_node_child_at_path(delimiter_for_key_of_system_user)

            # 添加授权的系统用户
            for system_user_id in system_users_id:
                self._append_path_to_data_tree_node(
                    data_tree_node=data_tree_node_of_asset_system_users, arg_path=system_user_id
                )

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
        assets_id = self.paths_of_assets_about_immediate_granted(asset_id_as_path=True)
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
        nodes_key = self.paths_of_nodes_about_immediate_granted()
        return list(set(nodes_key))

    def paths_of_assets_about_immediate_granted(self, asset_id_as_path=False):
        """
        return: 返回直接授权的资产
        arg - only_asset_id: 是否只返回资产id
        """

        def arg_callable_filter_of_asset_about_immediate_granted(arg_iterable_path, arg_node):
            if delimiter_for_key_of_immediate_granted_flag not in arg_iterable_path:
                return False
            if delimiter_for_key_of_asset not in arg_iterable_path:
                return False
            return True

        def arg_callable_formatter_of_asset_id_as_path(arg_iterable_path, arg_node):
            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            index_of_asset_id = index_of_delimiter_for_asset + 1
            asset_id = arg_iterable_path[index_of_asset_id]
            return asset_id

        def arg_callable_formatter_of_asset_path(arg_iterable_path, arg_node):
            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            index_of_asset_id = index_of_delimiter_for_asset + 1
            path_of_asset = arg_iterable_path[:index_of_asset_id+1]
            path = delimiter_for_path.join(path_of_asset)
            return path

        if asset_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_asset_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_asset_path

        _arg_callable_filter = arg_callable_filter_of_asset_about_immediate_granted

        paths = self._paths_of_data_tree_node(
            data_tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_nodes_about_immediate_granted(self):
        """返回直接授权的节点 """

        def arg_callable_filter_of_node_about_immediate_granted(arg_iterable_path, arg_node):
            if delimiter_for_key_of_immediate_granted_flag not in arg_iterable_path:
                return False
            index_of_immediate_granted_flag = arg_iterable_path.index(
                delimiter_for_key_of_immediate_granted_flag
            )
            path_of_before_immediate_granted_flag = \
                arg_iterable_path[:index_of_immediate_granted_flag]
            is_node_path = ''.join(path_of_before_immediate_granted_flag).isdigit()
            return is_node_path

        def arg_callable_formatter_of_node_path(arg_iterable_path, arg_node):
            index_of_immediate_granted_flag = arg_iterable_path.index(
                delimiter_for_key_of_immediate_granted_flag
            )
            path_of_node = arg_iterable_path[:index_of_immediate_granted_flag]
            return delimiter_for_path.join(path_of_node)

        _arg_callable_filter = arg_callable_filter_of_node_about_immediate_granted
        _arg_callable_formatter = arg_callable_formatter_of_node_path

        paths = self._paths_of_data_tree_node(
            data_tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths

    def paths_of_system_users_about_grant_to_asset(self, asset_id, system_user_id_as_path=False):
        """
        return: 返回授权给资产的系统用户
        arg - asset_id:
        arg - system_user_id_as_path: 是否将 system_user_id 作为路径
        """
        paths = []
        paths_about_immediate_granted = self.paths_of_system_users_about_immediate_grant_to_asset(
            asset_id=asset_id, system_user_id_as_path=system_user_id_as_path
        )
        paths_about_grant_to_nodes = []
        nodes_key_for_asset = self.get_nodes_key_for_asset(asset_id=asset_id)
        for _node_key in nodes_key_for_asset:
            paths_about_grant_to_node = self.paths_of_system_users_about_grant_to_node(
                node_key=_node_key, system_user_id_as_path=system_user_id_as_path
            )
            paths_about_grant_to_nodes.append(paths_about_grant_to_node)

        paths.extend(paths_about_immediate_granted)
        paths.extend(paths_about_grant_to_nodes)
        return paths

    def paths_of_system_users_about_grant_to_node(self, node_key, system_user_id_as_path=False):
        """
        return: 返回授权给节点的系统用户
        arg - node_key:
        arg - system_user_id_as_path: 是否将 system_user_id 作为路径
        """
        paths = []
        ancestor_nodes_key = self.compute_ancestor_node_key(node_key=node_key)
        for _node_key in ancestor_nodes_key:
            paths_about_grant_to_node = self.paths_of_system_users_about_immediate_grant_to_node(
                node_key=_node_key, system_user_id_as_path=system_user_id_as_path
            )
            paths.append(paths_about_grant_to_node)
        return paths

    def paths_of_system_users_about_immediate_grant_to_asset(self, asset_id, **kwargs):
        """
        return: 返回直接授权给资产的系统用户
        arg - asset_id: 指定资产id
        arg - only_system_user_id: 是否只返回系统用户id
        """
        system_user_id_as_path = kwargs.get('system_user_id_as_path', False)

        paths = self.paths_of_system_users_about_immediate_granted(
            asset_id=asset_id, system_user_id_as_path=system_user_id_as_path
        )
        return paths

    def paths_of_system_users_about_immediate_grant_to_node(self, node_key, **kwargs):
        """
        return: 返回直接授权给节点的系统用户
        arg - node_key:
        arg - system_user_id_as_path: 是否将 system_user_id 作为路径
        """

        system_user_id_as_path = kwargs.get('system_user_id_as_path', False)

        paths = self.paths_of_system_users_about_immediate_granted(
            node_key=node_key, system_user_id_as_path=system_user_id_as_path
        )
        return paths

    def paths_of_system_users_about_immediate_granted(self, asset_id=None, node_key=None, **kwargs):
        assert node_key is not None or asset_id is not None, (
            'At least one of `node_key` and `asset_id` is not `None`'
        )

        system_user_id_as_path = kwargs.get('system_user_id_as_path', False)

        def arg_callable_filter_of_immediate_grant_to_asset(arg_iterable_path, arg_node):
            if delimiter_for_key_of_system_user not in arg_iterable_path:
                return False

            if delimiter_for_key_of_asset not in arg_iterable_path:
                return False

            index_of_delimiter_for_system_user = \
                arg_iterable_path.index(delimiter_for_key_of_system_user)
            index_of_system_user_id = index_of_delimiter_for_system_user + 1
            if len(arg_iterable_path) != index_of_system_user_id + 1:
                return False

            index_of_delimiter_for_asset = arg_iterable_path.index(delimiter_for_key_of_asset)
            index_of_asset_id = index_of_delimiter_for_asset + 1
            _asset_id = index_of_asset_id[index_of_asset_id]

            return _asset_id == asset_id

        def arg_callable_filter_of_immediate_grant_to_node(arg_iterable_path, arg_node):
            if delimiter_for_key_of_system_user not in arg_iterable_path:
                return False

            index_of_delimiter_for_system_user = \
                arg_iterable_path.index(delimiter_for_key_of_system_user)

            path_of_before_delimiter_for_system_user = \
                arg_iterable_path[:index_of_delimiter_for_system_user]

            is_node_path = ''.join(path_of_before_delimiter_for_system_user).isdigit()
            if not is_node_path:
                return False

            _node_key = delimiter_for_path.join(path_of_before_delimiter_for_system_user)

            return _node_key == node_key

        def arg_callable_formatter_of_system_user_id_as_path(arg_iterable_path, arg_node):
            index_of_delimiter_for_system_user = \
                arg_iterable_path.index(delimiter_for_key_of_system_user)
            index_of_system_user_id = index_of_delimiter_for_system_user + 1
            system_user_id = arg_iterable_path[index_of_system_user_id]
            return system_user_id

        def arg_callable_formatter_of_system_user_path(arg_iterable_path, arg_node):
            index_of_delimiter_for_system_user = \
                arg_iterable_path.index(delimiter_for_key_of_system_user)
            index_of_system_user_id = index_of_delimiter_for_system_user + 1
            path_of_system_user = arg_iterable_path[:index_of_system_user_id + 1]
            path = delimiter_for_path.join(path_of_system_user)
            return path

        if asset_id is not None:
            _arg_callable_filter = arg_callable_filter_of_immediate_grant_to_asset
        elif node_key is not None:
            _arg_callable_filter = arg_callable_filter_of_immediate_grant_to_node
        else:
            return []

        if system_user_id_as_path:
            _arg_callable_formatter = arg_callable_formatter_of_system_user_id_as_path
        else:
            _arg_callable_formatter = arg_callable_formatter_of_system_user_path

        paths = self._paths_of_data_tree_node(
            data_tree_node=self._root,
            arg_callable_filter=_arg_callable_filter,
            arg_callable_formatter=_arg_callable_formatter
        )
        return paths


asset_permissions = AssetPermission.objects.filter(name='x')
asset_permission_tree = AssetPermissionTree(org_id='', permissions=asset_permissions)
print(asset_permission_tree.count_assets_of_node('1'))
print(asset_permission_tree.paths_of_nodes_about_immediate_granted())
print(asset_permission_tree.paths_of_assets_about_immediate_granted())


class NodeAssetTree(BaseTree):

    def __init__(self, base_tree: BaseTree, nodes, assets, *args, **kwargs):
        self._base_tree = base_tree
        self._nodes = nodes
        self._assets = assets
        super().__init__(*args, **kwargs)

    @timeit
    def initial(self, *args, **kwargs):
        nodes_key = list(self._nodes.values_list('key', flat=True))
        for node_key in nodes_key:
            arg_node = self._base_tree.get_data_tree_node(node_key=node_key)
            arg_node = Data_tree_node(arg_data=arg_node)
            self._append_path_to_data_tree_node(self._root, arg_path=node_key, arg_node=arg_node)

        assets_id = list(self._assets.values_list('id'))
        assets_id_nodes_key = Node.assets.through.objects.filter(asset_id__in=assets_id).values_list(
            'asset_id', 'node__key'
        )
        for asset_id, node_key in assets_id_nodes_key:
            path_keys_of_asset = [node_key, str(asset_id)]
            path_of_asset = delimiter_for_path.join(path_keys_of_asset)
            self._append_path_to_data_tree_node(data_tree_node=self._root, arg_path=path_of_asset)


class AssetSearchTree(BaseTree):
    """ 资产搜索树 """

    @property
    def asset_tree(self):
        return asset_tree

    def initial(self):
        pass
