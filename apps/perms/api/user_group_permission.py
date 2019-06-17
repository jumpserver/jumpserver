# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListAPIView, get_object_or_404,
)

from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from common.tree import TreeNodeSerializer
from orgs.utils import set_to_root_org
from ..utils import (
    AssetPermissionUtil, parse_asset_to_tree_node, parse_node_to_tree_node,
    RemoteAppPermissionUtil,
)
from ..hands import (
    AssetGrantedSerializer, UserGroup,  Node, NodeSerializer,
    RemoteAppSerializer,
)
from .. import serializers, const


__all__ = [
    'UserGroupGrantedAssetsApi', 'UserGroupGrantedNodesApi',
    'UserGroupGrantedNodesWithAssetsApi', 'UserGroupGrantedNodeAssetsApi',
    'UserGroupGrantedNodesWithAssetsAsTreeApi',
    'UserGroupGrantedRemoteAppsApi',
]


class UserGroupGrantedAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = []

        if not user_group_id:
            return queryset

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = AssetPermissionUtil(user_group)
        assets = util.get_assets()
        for k, v in assets.items():
            k.system_users_granted = v
            queryset.append(k)
        return queryset


class UserGroupGrantedNodesApi(ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = NodeSerializer

    def get_queryset(self):
        group_id = self.kwargs.get('pk', '')
        queryset = []

        if group_id:
            group = get_object_or_404(UserGroup, id=group_id)
            util = AssetPermissionUtil(group)
            nodes = util.get_nodes_with_assets()
            return nodes.keys()
        return queryset


class UserGroupGrantedNodesWithAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.NodeGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = []

        if not user_group_id:
            return queryset

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = AssetPermissionUtil(user_group)
        nodes = util.get_nodes_with_assets()
        for node, _assets in nodes.items():
            assets = _assets.keys()
            for asset, system_users in _assets.items():
                asset.system_users_granted = system_users
            node.assets_granted = assets
            queryset.append(node)
        return queryset


class UserGroupGrantedNodesWithAssetsAsTreeApi(ListAPIView):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    show_assets = True
    system_user_id = None

    def get(self, request, *args, **kwargs):
        self.show_assets = request.query_params.get('show_assets', '1') == '1'
        self.system_user_id = request.query_params.get('system_user')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = []
        group = get_object_or_404(UserGroup, id=user_group_id)
        util = AssetPermissionUtil(group)
        if self.system_user_id:
            util.filter_permissions(system_users=self.system_user_id)
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


class UserGroupGrantedNodeAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        node_id = self.kwargs.get('node_id')

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = AssetPermissionUtil(user_group)
        if str(node_id) == const.UNGROUPED_NODE_ID:
            node = util.tree.ungrouped_node
        else:
            node = get_object_or_404(Node, id=node_id)
        nodes = util.get_nodes_with_assets()
        assets = nodes.get(node, [])
        for asset, system_users in assets.items():
            asset.system_users_granted = system_users
        return assets


# RemoteApp permission

class UserGroupGrantedRemoteAppsApi(ListAPIView):
    permission_classes = (IsOrgAdmin, )
    serializer_class = RemoteAppSerializer

    def get_queryset(self):
        queryset = []
        user_group_id = self.kwargs.get('pk')
        if not user_group_id:
            return queryset
        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = RemoteAppPermissionUtil(user_group)
        queryset = util.get_remote_apps()
        return queryset
