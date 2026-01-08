from rest_framework import generics
from rest_framework.response import Response

from rbac.permissions import RBACPermission
from .mixin import SerializeToTreeNodeMixin
from assets.models import Node
from assets.tree.asset_tree import AssetGenericTree
from orgs.utils import current_org, tmp_to_org
from orgs.models import Organization
from common.utils import timeit


__all__ = ['AssetGenericTreeApi', 'AssetNodeTreeApi', 'AssetTypeTreeApi']


class AssetGenericTreeApi(SerializeToTreeNodeMixin, generics.ListAPIView):
    permission_classes = (RBACPermission, )

    rbac_perms = {
        'list': 'assets.view_asset',
        'GET': 'assets.view_asset',
        'OPTIONS': 'assets.view_asset',
    }
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.initial_node_root_if_need()

    @property
    def tree_user(self):
        return self.request.user

    @property
    def tree_orgs(self):
        if current_org.is_root():
            orgs = self.tree_user.orgs.all()
        else:
            orgs = Organization.objects.filter(id=current_org.id)
        return orgs
    
    def initial_node_root_if_need(self):
        for org in self.tree_orgs:
            with tmp_to_org(org):
                Node.org_root()

    @timeit
    def list(self, request, *args, **kwargs):
        data = []
        for org in self.tree_orgs:
            tree = self.get_asset_tree(org)
            tree_data = self.get_tree_data(tree)
            data.extend(tree_data)
        return Response(data=data)

    def get_asset_tree(self, org) -> AssetGenericTree:
        raise NotImplementedError()
    
    def get_tree_data(self, tree):
        tree: AssetGenericTree
        if tree.empty():
            return []

        with_assets = self.request.query_params.get('assets', '0') == '1'
        with_assets_amount = self.request.query_params.get('asset_amount', '1') == '1'
        with_assets_amount = True
        expand_node_key = self.request.query_params.get('key')
        search = self.request.query_params.get('search')
        if search:
            nodes = tree.filter_nodes(keyword=search)
            ancestors = tree.get_ancestors_of_nodes(nodes)
            nodes = tree.merge_nodes(ancestors, nodes)
            data_nodes = self.serialize_nodes(ancestors, with_asset_amount=with_assets_amount)
            if with_assets:
                assets = tree.filter_assets(keyword=search)
                node_key = tree.root.key
                data_assets = self.serialize_assets(assets, node_key=node_key)
                return data_nodes + data_assets
            return data_nodes

        if expand_node_key:
            node = tree.get_node(expand_node_key)
            if not node:
                return []
            nodes = node.children
            data_nodes = self.serialize_nodes(nodes, with_asset_amount=with_assets_amount)
            if with_assets:
                assets = tree.filter_assets(node_key=expand_node_key)
                data_assets = self.serialize_assets(assets, node_key=expand_node_key)
                return data_nodes + data_assets
            return data_nodes

        data_assets = []
        if current_org.is_root():
            nodes = [tree.root]
        else:
            nodes = [tree.root] + tree.root.children
            if with_assets:
                assets = tree.filter_assets(node_key=tree.root.key)
                data_assets = self.serialize_assets(assets, node_key=tree.root.key)
        data_nodes = self.serialize_nodes(nodes, with_asset_amount=with_assets_amount)
        data = data_nodes + data_assets
        return data


class AssetNodeTreeApi(AssetGenericTreeApi):

    def get_asset_tree(self, org):
        from assets.tree.node_tree import AssetNodeTree
        category = self.request.query_params.get('category')
        tree = AssetNodeTree(category=category, org=org)
        tree.init()
        return tree

    def get_tree_data(self, tree):
        from assets.tree.node_tree import AssetNodeTree
        tree: AssetNodeTree
        expand_node_key = self.request.query_params.get('key')
        search = self.request.query_params.get('search')
        if search or expand_node_key:
            tree.set_use_cache()
        return super().get_tree_data(tree)


class AssetTypeTreeApi(AssetGenericTreeApi):

    def get_asset_tree(self, org):
        from assets.tree.type_tree import AssetTypeTree
        tree = AssetTypeTree(org=org)
        tree.init()
        return tree