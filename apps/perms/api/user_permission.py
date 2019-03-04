# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404,
)
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.tree import TreeNodeSerializer
from orgs.utils import set_to_root_org
from ..utils import (
    AssetPermissionUtil, parse_asset_to_tree_node, parse_node_to_tree_node
)
from ..hands import (
    AssetGrantedSerializer, User, Asset, Node,
    SystemUser, NodeSerializer
)
from .. import serializers
from ..mixins import AssetsFilterMixin


__all__ = [
    'UserGrantedAssetsApi', 'UserGrantedNodesApi',
    'UserGrantedNodesWithAssetsApi', 'UserGrantedNodeAssetsApi',
    'ValidateUserAssetPermissionApi', 'UserGrantedNodeChildrenApi',
    'UserGrantedNodesWithAssetsAsTreeApi',
]


class UserPermissionMixin:
    cache_policy = '0'

    @staticmethod
    def change_org_if_need(request, kwargs):
        if request.user.is_superuser or \
                request.user.is_app or \
                kwargs.get('pk') is None:
            set_to_root_org()

    def dispatch(self, request, *args, **kwargs):
        self.change_org_if_need(request, kwargs)
        self.cache_policy = request.GET.get('cache_policy', '0')
        return super().dispatch(request, *args, **kwargs)


class UserGrantedAssetsApi(UserPermissionMixin, AssetsFilterMixin, ListAPIView):
    """
    用户授权的所有资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        queryset = []

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user

        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        assets = util.get_assets()
        for k, v in assets.items():
            system_users_granted = [s for s in v if s.protocol == k.protocol]
            k.system_users_granted = system_users_granted
            queryset.append(k)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesApi(UserPermissionMixin, ListAPIView):
    """
    查询用户授权的所有节点的API, 如果是超级用户或者是 app，切换到root org
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = NodeSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        nodes = util.get_nodes_with_assets()
        return nodes.keys()

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesWithAssetsApi(UserPermissionMixin, AssetsFilterMixin, ListAPIView):
    """
    用户授权的节点并带着节点下资产的api
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.NodeGrantedSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        queryset = []
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)

        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        nodes = util.get_nodes_with_assets()
        for node, _assets in nodes.items():
            assets = _assets.keys()
            for k, v in _assets.items():
                system_users_granted = [s for s in v if
                                        s.protocol == k.protocol]
                k.system_users_granted = system_users_granted
            node.assets_granted = assets
            queryset.append(node)
        return queryset

    def sort_assets(self, queryset):
        for node in queryset:
            node.assets_granted = super().sort_assets(node.assets_granted)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesWithAssetsAsTreeApi(UserPermissionMixin, ListAPIView):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    show_assets = True
    system_user_id = None

    def get(self, request, *args, **kwargs):
        self.show_assets = request.query_params.get('show_assets', '1') == '1'
        self.system_user_id = request.query_params.get('system_user')
        return super().get(request, *args, **kwargs)

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        queryset = []
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        if self.system_user_id:
            util.filter_permission_with_system_user(
                system_user=self.system_user_id)
        nodes = util.get_nodes_with_assets()
        for node, assets in nodes.items():
            data = parse_node_to_tree_node(node)
            queryset.append(data)
            if not self.show_assets:
                continue
            for asset, system_users in assets.items():
                data = parse_asset_to_tree_node(node, asset, system_users)
                queryset.append(data)
        queryset = sorted(queryset)
        return queryset


class UserGrantedNodeAssetsApi(UserPermissionMixin, AssetsFilterMixin, ListAPIView):
    """
    查询用户授权的节点下的资产的api, 与上面api不同的是，只返回某个节点下的资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        node_id = self.kwargs.get('node_id')

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        node = get_object_or_404(Node, id=node_id)
        nodes = util.get_nodes_with_assets()
        assets = nodes.get(node, [])
        for asset, system_users in assets.items():
            asset.system_users_granted = system_users

        assets = list(assets.keys())
        return assets

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodeChildrenApi(UserPermissionMixin, ListAPIView):
    """
    获取用户自己授权节点下子节点的api
    """
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AssetPermissionNodeSerializer

    def get_children_queryset(self):
        util = AssetPermissionUtil(self.request.user, cache_policy=self.cache_policy)
        node_id = self.request.query_params.get('id')
        nodes_granted = util.get_nodes_with_assets()
        if not nodes_granted:
            return []
        root_nodes = [node for node in nodes_granted.keys() if node.is_root()]

        queryset = []
        if node_id and node_id in [str(node.id) for node in nodes_granted]:
            node = [node for node in nodes_granted if str(node.id) == node_id][0]
        elif len(root_nodes) == 1:
            node = root_nodes[0]
            node.assets_amount = len(nodes_granted[node])
            queryset.append(node)
        else:
            for node in root_nodes:
                node.assets_amount = len(nodes_granted[node])
                queryset.append(node)
            return queryset

        children = []
        for child in node.get_children():
            if child in nodes_granted:
                child.assets_amount = len(nodes_granted[node])
                children.append(child)
        children = sorted(children, key=lambda x: x.value)
        queryset.extend(children)
        fake_nodes = []
        for asset, system_users in nodes_granted[node].items():
            fake_node = asset.as_node()
            fake_node.assets_amount = 0
            system_users = [s for s in system_users if s.protocol == asset.protocol]
            fake_node.asset.system_users_granted = system_users
            fake_node.key = node.key + ':0'
            fake_nodes.append(fake_node)
        fake_nodes = sorted(fake_nodes, key=lambda x: x.value)
        queryset.extend(fake_nodes)
        return queryset

    def get_search_queryset(self, keyword):
        util = AssetPermissionUtil(self.request.user, cache_policy=self.cache_policy)
        nodes_granted = util.get_nodes_with_assets()
        queryset = []
        for node, assets in nodes_granted.items():
            matched_assets = []
            node_matched = node.value.lower().find(keyword.lower()) >= 0
            asset_has_matched = False
            for asset, system_users in assets.items():
                asset_matched = (asset.hostname.lower().find(keyword.lower()) >= 0) \
                                or (asset.ip.find(keyword.lower()) >= 0)
                if node_matched or asset_matched:
                    asset_has_matched = True
                    fake_node = asset.as_node()
                    fake_node.assets_amount = 0
                    system_users = [s for s in system_users if
                                    s.protocol == asset.protocol]
                    fake_node.asset.system_users_granted = system_users
                    fake_node.key = node.key + ':0'
                    matched_assets.append(fake_node)
            if asset_has_matched:
                node.assets_amount = len(matched_assets)
                queryset.append(node)
                queryset.extend(sorted(matched_assets, key=lambda x: x.value))
        return queryset

    def get_queryset(self):
        keyword = self.request.query_params.get('search')
        if keyword:
            return self.get_search_queryset(keyword)
        else:
            return self.get_children_queryset()


class ValidateUserAssetPermissionApi(UserPermissionMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        assets_granted = util.get_assets()
        if system_user in assets_granted.get(asset, []):
            return Response({'msg': True}, status=200)
        else:
            return Response({'msg': False}, status=403)


