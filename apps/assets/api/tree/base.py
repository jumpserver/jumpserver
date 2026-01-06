from abc import abstractmethod, abstractproperty

from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from users.models import User
from common.utils import lazyproperty, timeit
from common.exceptions import APIException
from orgs.utils import current_org
from rbac.permissions import RBACPermission
from assets.models import Node
from assets.tree.node_tree import AssetNodeTree, NodeTreeNode
from .mixin import SerializeToTreeNodeMixin
from .const import RenderTreeView, RenderTreeViewChoices


__all__ = ['AbstractAssetTreeAPI']


class AbstractAssetTreeAPI(SerializeToTreeNodeMixin, generics.ListAPIView):

    # 子类必须指定权限 rbac_perms#
    permission_classes = (RBACPermission,)

    # query parameters keys
    query_search_key = 'search'
    query_search_key_value_sep = ':'
    query_tree_view_key = 'tree_view'
    query_asset_category_key = 'category'
    query_asset_type_key = 'type'
    query_search_asset_key = 'search_asset'
    query_search_node_key = 'search_node'
    # 以上参数均支持通过 search 参数传递，格式如 search=key:value
    # 也支持直接通过对应的 query parameter 传递，如 ?search_node=demo_node&type=linux
    query_expand_node_key = 'key'

    # 每个组织树搜索资产时，返回的资产数量限制
    search_assets_per_org_limit_max = 1000
    search_assets_per_org_limit_min = 100

    @lazyproperty
    def tree_with_assets(self):
        with_assets = self.request.query_params.get('assets', '0') == '1'
        return with_assets

    @lazyproperty
    def tree_view(self):
        # 资产树视图 # 默认是节点视图 # 扩展支持 category 视图, label 视图等等
        tree_view = self.get_query_value(self.query_tree_view_key)
        tree_view = tree_view or RenderTreeViewChoices.node
        return RenderTreeView(tree_view)

    @lazyproperty
    def tree_user(self) -> User:
        return self.get_tree_user()
    
    def get_tree_user(self) -> User:
        # 抽象方法: 获取为哪个用户渲染树 #
        raise NotImplementedError

    def get_query_value(self, query_key):
        query_value = self.request.query_params.get(query_key)
        if not query_value:
            query_value = self.get_query_value_from_search(query_key)
        return query_value
    
    def get_query_value_from_search(self, query_key):
        # 辅助方法：获取查询的参数，支持在 search 参数中以 key:value 形式传递 #
        search = self.request.query_params.get(self.query_search_key, '')
        if not search:
            return None
        
        sep = self.query_search_key_value_sep

        search_list = search.split()
        for _search in search_list:
            if f'{query_key}{sep}' not in _search:
                continue
            query_value = _search.replace(f'{query_key}{sep}', '').strip()
            return query_value
    
    @abstractmethod
    def get_asset_tree(self, assets_scope_q=None, asset_category=None, asset_type=None, org=None):
        raise NotImplementedError

    @lazyproperty
    def tree_user_orgs(self):
        # 重要: 获取用户有权限渲染树的组织列表 #
        orgs = self.tree_user.orgs.all()
        if not current_org.is_root():
            orgs = orgs.filter(id=current_org.id)
        if not orgs.exists():
            raise APIException('No organization available for rendering the tree')
        return orgs
    
    def get_search_asset_keyword(self):
        search_asset = self.get_query_value(self.query_search_asset_key)
        if self.tree_with_assets and not search_asset:
            # 兼容 search 为搜索资产
            search = self.get_query_value(self.query_search_key) or ''
            search_asset = search if self.query_search_key_value_sep not in search else ''
        return search_asset

    @timeit
    def list(self, request, *args, **kwargs):
        # 渲染资产树 API 接口 #
        asset_category = self.get_query_value(self.query_asset_category_key)
        asset_type = self.get_query_value(self.query_asset_type_key)
        with_asset_amount = True

        expand_node_key = self.get_query_value(self.query_expand_node_key)
        search_node = self.get_query_value(self.query_search_node_key)
        search_asset = self.get_search_asset_keyword()

        data = []
        for org in self.tree_user_orgs:
            nodes, assets = self.get_org_nodes_assets_data(
                org=org,
                expand_node_key=expand_node_key,
                search_node=search_node,
                search_asset=search_asset,
                asset_category=asset_category,
                asset_type=asset_type,
                with_asset_amount=with_asset_amount
            )
            data.extend(nodes)
            data.extend(assets)
        return Response(data=data)
    
    def get_org_nodes_assets_data(
            self, org, expand_node_key=None, search_node=None, search_asset=None, 
            asset_category=None, asset_type=None, with_asset_amount=True
        ):

        tree = self.get_asset_tree(
            search_asset=search_asset, asset_category=asset_category, asset_type=asset_type, 
            org=org, with_asset_amount=with_asset_amount
        )

        nodes = []
        assets = []
        if self.tree_with_assets:
            if expand_node_key:
                node = tree.get_node(key=expand_node_key)
                if not node:
                    raise APIException(f'Node not found: {expand_node_key}')
                nodes = node.children
                assets = tree.get_tree_assets(nodes=[node])
            elif search_node:
                # 只展开父节点
                pass
            elif search_asset:
                nodes = tree.get_nodes(with_empty_assets_branch=False)
                assets = tree.get_tree_assets(limit=10)
                for node in nodes:
                    if node.key == '1:0:1:1:0':
                        print('.........')
                    node: NodeTreeNode
                    setattr(node, 'is_parent', False)
                    setattr(node, 'open', True)
            else:
                if current_org.is_root():
                    nodes = [tree.root]
                else:
                    tree_root = tree.root
                    setattr(tree_root, 'open', True)
                    nodes = [tree_root] + tree_root.children
                    assets = tree.get_tree_assets(nodes=[tree_root])
            
            for node in nodes:
                node: NodeTreeNode
                is_parent = not node.is_leaf or node.assets_amount > 0
                setattr(node, 'is_parent', is_parent)

        else:
            nodes = tree.get_nodes()
            if not current_org.is_root():
                setattr(tree.root, 'open', True)

            for node in nodes:
                node: NodeTreeNode
                is_parent = not node.is_leaf
                setattr(node, 'is_parent', is_parent)
        
        if with_asset_amount:
            for node in nodes:
                node.name = f'{node.name} ({node.assets_amount_total})'

        data_nodes = self.serialize_nodes(nodes=nodes)
        data_assets = self.serialize_assets(assets)
        return data_nodes, data_assets

    
    def get_asset_tree(self, search_asset=None, asset_category=None, asset_type=None, org=None, 
                       with_asset_amount=True):
        assets_scope_q = None
        if search_asset:
            assets_scope_q = Q(name__icontains=search_asset) | Q(address__icontains=search_asset)
        tree = AssetNodeTree(
            assets_scope_q=assets_scope_q, 
            asset_category=asset_category, 
            asset_type=asset_type, 
            org=org
        )
        tree.init(with_assets_amount=with_asset_amount)
        return tree
    
    @timeit
    def _list(self, expand_node_key=None, search_node=None, search_asset=None,
              asset_category=None, asset_type=None, with_asset_amount=True):

        if not self.tree_with_assets:
            data = self.render_node_tree(
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        elif self.render_tree_type.is_asset_tree:
            data = self.render_asset_tree(
                expand_node_key=expand_node_key, 
                search_node=search_node, search_asset=search_asset,
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        else:
            raise APIException(
                f'Invalid tree type: {self.render_tree_type}'
            )
        return data

    @timeit
    def render_node_tree(self, asset_category=None, asset_type=None, with_asset_amount=True):
        # 渲染节点树 #
        # 节点树返回所有节点的数据，不返回资产
        # 节点树只有初始化
        # 搜索节点和展开节点的动作，在前端页面执行
        data = self.init_node_tree(
            asset_category=asset_category, 
            asset_type=asset_type, 
            with_asset_amount=with_asset_amount
        )
        return data

    @timeit
    def render_asset_tree(self, expand_node_key=None, search_node=None, search_asset=None, 
                           asset_category=None, asset_type=None, with_asset_amount=True):
        # 渲染资产树内部方法，支持子类重载 #
        # 此方法包含渲染资产树的所有参数
        # 资产树支持初始化、搜索节点、搜索资产和展开节点等动作

        if expand_node_key:
            data = self.expand_asset_tree_node(
                node_key=expand_node_key, 
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        elif search_node:
            data = self.search_asset_tree_nodes(
                search_node=search_node, 
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        elif search_asset:
            data = self.search_asset_tree_assets(
                search_asset=search_asset, 
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        else:
            data = self.init_asset_tree(
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        return data
    
    @timeit
    def init_node_tree(self, asset_category=None, asset_type=None, with_asset_amount=True):
        orgs = self.get_tree_user_orgs()

        if self.org_is_global:
            expand_level = 0
        else:
            expand_level = 1

        nodes = []
        for org in orgs:
            tree = self.get_asset_tree(
                asset_category=asset_category, asset_type=asset_type, org=org
            )
            _nodes = tree.get_nodes()
            nodes.extend(_nodes)

        data = self.serialize_nodes(
            nodes=nodes, tree_type=self.render_tree_type, 
            with_asset_amount=with_asset_amount, expand_level=expand_level
        )
        return data
    
    @timeit
    def init_asset_tree(self, asset_category=None, asset_type=None, with_asset_amount=True):
        orgs = self.get_tree_user_orgs()
        if self.org_is_global:
            node_levels = [1]
            with_assets_node_levels = None
            expand_level = 0
        else:
            node_levels = [1, 2]
            with_assets_node_levels = [1]
            expand_level = 1
        nodes = []
        assets = []
        for org in orgs:
            tree = self.get_asset_tree(
                asset_category=asset_category, 
                asset_type=asset_type, 
                org=org, 
                with_assets_node_levels=with_assets_node_levels
            )
            _nodes = tree.get_nodes(levels=node_levels)
            nodes.extend(_nodes)
            _assets = tree.get_assets()
            assets.extend(_assets)
        
        serialized_nodes = self.serialize_nodes(
            nodes=nodes, tree_type=self.render_tree_type, 
            with_asset_amount=with_asset_amount, 
            expand_level=expand_level
        )
        serialized_assets = self.serialize_assets(assets)
        data = serialized_nodes + serialized_assets
        return data

    @timeit
    def expand_asset_tree_node(self, node_key,  asset_category=None, asset_type=None, 
                               with_asset_amount=True):
        # 展开资产树节点 #
        # 展开节点时，返回该节点的直接子节点和直接资产

        if self.render_tree_view.is_node_view:
            node = get_object_or_404(Node, key=node_key)
            node_id = str(node.id)
            orgs = self.get_tree_user_orgs()
            org = orgs.filter(id=node.org_id).first()
            if not org:
                # 确保用户有权限展开该节点所在组织的树
                raise APIException(
                    f'No permission to expand the node in this organization: {node.org_name}'
                )
        else:
            assert not self.org_is_global, 'Category view is not supported in global org'
            org = self.get_tree_user_orgs().first()
            assert org, 'User has no organization for rendering the tree'
            node_id = node_key  # 在类别视图中，节点 key 就是节点 id
        
        with_assets_node_id = node_id
        tree = self.get_asset_tree(
            asset_category=asset_category, 
            asset_type=asset_type, 
            org=org,
            with_assets_node_id=with_assets_node_id
        )
        node_children = tree.get_node_children(node_key)
        node_assets = tree.get_assets()

        # (展开节点)的孩子节点不展开
        expand_level = 0
        serialized_nodes = self.serialize_nodes(
            nodes=node_children, 
            tree_type=self.render_tree_type, 
            with_asset_amount=with_asset_amount, 
            expand_level=expand_level
        )
        serialized_assets = self.serialize_assets(node_assets)
        data = serialized_nodes + serialized_assets
        return data

    @timeit
    def search_asset_tree_nodes(self, search_node, asset_category=None, asset_type=None, 
                                with_asset_amount=True):
        # 搜索资产树节点 #
        # 搜索节点时，返回匹配的节点和匹配节点的所有祖先节点
        # 匹配节点中如果包含有父子关系的节点，只返回最上一级的父节点
        # 祖先节点全部展开
        # 匹配节点不展开

        orgs = self.get_tree_user_orgs()

        matched_nodes = []
        matched_nodes_ancestors = []
        for org in orgs:
            tree = self.get_asset_tree(
                asset_category=asset_category, 
                asset_type=asset_type, 
                org=org
            )
            # 如果匹配的节点中包含有父子关系的节点，只返回最上一级的父节点
            _matched_nodes = tree.search_nodes(search_node, only_top_level=True)
            if not _matched_nodes:
                continue
            matched_nodes.extend(_matched_nodes)
            _ancestors = tree.get_nodes_ancestors(_matched_nodes)
            matched_nodes_ancestors.extend(_ancestors)
        
        if not matched_nodes:
            return []
        
        # 匹配的节点不展开
        expand_level = 0
        serialized_matched_nodes = self.serialize_nodes(
            nodes=matched_nodes, tree_type=self.render_tree_type, 
            with_asset_amount=with_asset_amount, 
            expand_level=expand_level
        )

        # 匹配节点的祖先节点全部展开
        expand_all = True
        serialized_ancestors = self.serialize_nodes(
            nodes=matched_nodes_ancestors, 
            tree_type=self.render_tree_type, 
            with_asset_amount=with_asset_amount, 
            expand_level=expand_level,
            expand_all=expand_all
        )
        data = serialized_matched_nodes + serialized_ancestors
        return data

    @timeit
    def search_asset_tree_assets(self, search_asset, asset_category=None, asset_type=None, 
                                 with_asset_amount=True):
        # 搜索资产树资产 #
        # 搜索资产时，返回包含匹配资产所在的节点及其祖先节点，以及匹配的资产
        # 所有节点全部展开

        orgs = self.get_tree_user_orgs()

        # 搜索时，展开所有节点
        expand_all = True

        # 资产树搜索范围
        assets_q_object = Q(name__icontains=search_asset) | Q(address__icontains=search_asset)

        # 限制每个组织搜索返回的资产数量
        with_assets_limit_max = self.search_assets_per_org_limit_max
        with_assets_limit_min = self.search_assets_per_org_limit_min
        with_assets_limit = max(
            with_assets_limit_min, 
            with_assets_limit_max // max(1, orgs.count())
        )

        # 搜索树只返回包含资产的节点
        full_tree = False

        nodes = []
        assets = []
        for org in orgs:
            tree = self.get_asset_tree(
                assets_q_object=assets_q_object,
                asset_category=asset_category, 
                asset_type=asset_type, org=org,
                with_assets_all=True, 
                with_assets_limit=with_assets_limit, 
                full_tree=full_tree
            )
            _nodes = tree.get_nodes()
            nodes.extend(_nodes)
            _assets = tree.get_assets()
            assets.extend(_assets)
        serialized_nodes = self.serialize_nodes(
            nodes=nodes, tree_type=self.render_tree_type, 
            with_asset_amount=with_asset_amount, 
            expand_all=expand_all
        )
        serialized_assets = self.serialize_assets(assets)
        data = serialized_nodes + serialized_assets
        return data
