
from django.db.models import Q
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from users.models import User
from common.utils import lazyproperty, timeit
from common.exceptions import APIException
from orgs.utils import current_org
from orgs.models import Organization
from rbac.permissions import RBACPermission
from assets.tree.asset_tree import AssetTree
from assets.models import Node
from .mixin import SerializeToTreeNodeMixin
from .const import RenderTreeType, RenderTreeTypeChoices


__all__ = ['AbstractAssetTreeAPI']


class AbstractAssetTreeAPI(SerializeToTreeNodeMixin, generics.ListAPIView):

    permission_classes = (RBACPermission,)

    # TODO: 再确认一下 API 所需的权限位
    perm_model = Node

    # query parameters keys
    query_search_key = 'search'
    query_search_key_value_sep = ':'
    query_tree_type_key = 'tree_type'
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

    render_tree_type: RenderTreeType

    tree_user: User

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.render_tree_type = self.initial_render_tree_type()
        self.tree_user = self.get_tree_user()

    def initial_render_tree_type(self):
        tree_type = self.get_query_value(self.query_tree_type_key)
        if not tree_type:
            # 兼容 assets=1 参数
            with_assets = self.request.query_params.get('assets', '0') == '1'
            if with_assets:
                tree_type = RenderTreeTypeChoices.asset
            else:
                tree_type = RenderTreeTypeChoices.node
        return RenderTreeType(tree_type)

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
    
    def get_org_asset_tree(self, **kwargs) -> AssetTree:
        # 抽象方法: 获取组织的资产树 #
        raise NotImplementedError

    @lazyproperty
    def org_is_global(self):
        return current_org.is_root()

    def get_tree_user_orgs(self):
        # 重要: 获取用户有权限渲染树的组织列表 #
        user = self.tree_user
        if self.org_is_global:
            # 如果是全局组织，返回用户所在的所有实体组织
            orgs = user.orgs.all()
        else:
            # 如果时实体组织，从用户所在的实体组织中返回该实体组织
            orgs = user.orgs.filter(id=current_org.id)
        if not orgs.exists():
            raise APIException(
                'No organization available for rendering the tree'
            )
        return orgs

    @timeit
    def list(self, request, *args, **kwargs):
        # 渲染资产树 API 接口 #
        # 支持渲染节点树和资产树两种类型
        # 节点树: 只返回节点
        # 资产树: 返回节点和节点下的资产
        asset_category = self.get_query_value(self.query_asset_category_key)
        asset_type = self.get_query_value(self.query_asset_type_key)
        with_asset_amount = True

        if self.render_tree_type.is_node_tree:
            data = self.render_node_tree(
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        elif self.render_tree_type.is_asset_tree:
            data = self.render_asset_tree(
                asset_category=asset_category, asset_type=asset_type, 
                with_asset_amount=with_asset_amount
            )
        else:
            raise APIException(
                f'Invalid tree type: {self.render_tree_type}'
            )
        return Response(data=data)

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
    def render_asset_tree(self, asset_category=None, asset_type=None, with_asset_amount=True):
        # 渲染资产树 #
        expand_node_key = self.get_query_value(self.query_expand_node_key)
        search_node = self.get_query_value(self.query_search_node_key)
        search_asset = self.get_query_value(self.query_search_asset_key)
        data = self._render_asset_tree(
            expand_node_key=expand_node_key, 
            search_node=search_node, search_asset=search_asset, 
            asset_category=asset_category, asset_type=asset_type, 
            with_asset_amount=with_asset_amount
        )
        return data

    @timeit
    def _render_asset_tree(self, expand_node_key=None, search_node=None, search_asset=None, 
                           asset_category=None, asset_type=None, with_asset_amount=True):
        # 渲染资产树内部方法，支持子类重载 #
        # 此方法包含渲染资产树的所有参数
        # 资产树支持初始化、搜索节点、搜索资产和展开节点等动作

        if not search_asset:
            # 兼容 search 为搜索资产
            search = self.get_query_value(self.query_search_key) or ''
            sep = self.query_search_key_value_sep
            if sep not in search:
                search_asset = search

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
            tree = self.get_org_asset_tree(
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
            tree: AssetTree = self.get_org_asset_tree(
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

        node = get_object_or_404(Node, key=node_key)
        orgs = self.get_tree_user_orgs()
        org = orgs.filter(id=node.org_id).first()
        if not org:
            # 确保用户有权限展开该节点所在组织的树
            raise APIException(
                f'No permission to expand the node in this organization: {node.org_name}'
            )
        
        with_assets_node_id = str(node.id)
        tree: AssetTree = self.get_org_asset_tree(
            asset_category=asset_category, 
            asset_type=asset_type, 
            org=org,
            with_assets_node_id=with_assets_node_id
        )
        node_children = tree.get_node_children(node.key)
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
            tree: AssetTree = self.get_org_asset_tree(
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
            tree: AssetTree = self.get_org_asset_tree(
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
