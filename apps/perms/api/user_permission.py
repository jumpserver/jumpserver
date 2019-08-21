# -*- coding: utf-8 -*-
#
import uuid

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveAPIView
)

from common.permissions import IsValidUser, IsOrgAdminOrAppUser, IsOrgAdmin
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from orgs.utils import set_to_root_org
from ..utils import (
    ParserNode, AssetPermissionUtilV2
)
from .mixin import (
    UserPermissionCacheMixin, GrantAssetsMixin, NodesWithUngroupMixin
)
from .. import const
from ..hands import User, Asset, Node, SystemUser, NodeSerializer
from .. import serializers
from ..models import Action


logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetsApi', 'UserGrantedNodesApi',
    'UserGrantedNodeAssetsApi',
    'ValidateUserAssetPermissionApi',
    'UserGrantedNodesWithAssetsAsTreeApi', 'GetUserAssetPermissionActionsApi',
    'RefreshAssetPermissionCacheApi', 'UserGrantedAssetSystemUsersApi',
    'UserGrantedNodeChildrenAsTreeApi', 'UserGrantedNodesWithAssetsAsTreeApi',
]


class UserPermissionMixin:
    permission_classes = (IsOrgAdminOrAppUser,)
    obj = None

    def initial(self, *args, **kwargs):
        super().initial(*args, *kwargs)
        self.obj = self.get_object()

    def get(self, request, *args, **kwargs):
        set_to_root_org()
        return super().get(request, *args, **kwargs)

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedAssetsApi(UserPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip']
    search_fields = filter_fields

    def filter_by_nodes(self, queryset):
        node_id = self.request.query_params.get("node")
        if not node_id:
            return queryset
        node = get_object_or_404(Node, pk=node_id)
        query_all = self.request.query_params.get("all", "0") in ["1", "true"]
        if query_all:
            pattern = '^{0}$|^{0}:'.format(node.key)
            queryset = queryset.filter(nodes__key__regex=pattern).distinct()
        else:
            queryset = queryset.filter(nodes=node)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_by_nodes(queryset)
        return queryset

    def get_queryset(self):
        util = AssetPermissionUtilV2(self.obj)
        queryset = util.get_assets().only(*self.only_fields)
        return queryset


class UserGrantedNodeAssetsApi(UserGrantedAssetsApi):
    def get_queryset(self):
        node_id = self.kwargs.get("node_id")
        node = get_object_or_404(Node, pk=node_id)
        deep = self.request.query_params.get("all", "0") == "1"
        util = AssetPermissionUtilV2(self.obj)
        queryset = util.get_nodes_assets(node, deep=deep)\
            .only(*self.only_fields)
        return queryset


class UserGrantedNodesApi(UserPermissionMixin, ListAPIView):
    """
    查询用户授权的所有节点的API
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.GrantedNodeSerializer
    only_fields = NodeSerializer.Meta.only_fields

    def get_queryset(self):
        util = AssetPermissionUtilV2(self.obj)
        node_keys = util.get_nodes()
        queryset = Node.objects.filter(key__in=node_keys)
        return queryset


class UserGrantedNodeChildrenApi(UserGrantedNodesApi):
    node = None
    util = None
    tree = None
    root_keys = None

    def get(self, request, *args, **kwargs):
        key = self.request.query_params.get("key")
        pk = self.request.query_params.get("id")
        system_user_id = self.request.query_params.get("system_user")
        self.util = AssetPermissionUtilV2(self.obj)
        if system_user_id:
            system_user = get_object_or_404(SystemUser, id=system_user_id)
            self.util.filter_permissions(system_users=system_user_id)
        self.tree = self.util.get_user_tree()

        node = None
        if pk is not None:
            node = get_object_or_404(Node, id=pk)
        elif key is not None:
            node = get_object_or_404(Node, key=key)
        self.node = node
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if self.node:
            children = self.tree.children(self.node.key)
        else:
            children = self.tree.children(self.tree.root)
            # 默认打开组织节点下的的节点
            self.root_keys = [child.identifier for child in children]
            for key in self.root_keys:
                children.extend(self.tree.children(key))
        node_keys = [n.identifier for n in children]
        queryset = Node.objects.filter(key__in=node_keys)
        return queryset


class UserGrantedNodeChildrenAsTreeApi(UserGrantedNodeChildrenApi):
    serializer_class = TreeNodeSerializer
    only_fields = ParserNode.nodes_only_fields

    def get_queryset(self):
        nodes = super().get_queryset()
        queryset = []
        for node in nodes:
            node._assets_amount = self.tree.assets_amount(node.key)
            data = ParserNode.parse_node_to_tree_node(node)
            queryset.append(data)
        return queryset


class UserGrantedNodesWithAssetsAsTreeApi(UserGrantedNodeChildrenAsTreeApi):
    nodes_only_fields = ParserNode.nodes_only_fields
    assets_only_fields = ParserNode.assets_only_fields

    def get_queryset(self):
        queryset = super().get_queryset()
        nodes = []
        if self.node:
            nodes.append(self.node)
        elif self.root_keys:
            nodes = Node.objects.filter(key__in=self.root_keys)

        for node in nodes:
            assets = self.util.get_nodes_assets(node).only(*self.assets_only_fields)
            for asset in assets:
                data = ParserNode.parse_asset_to_tree_node(node, asset)
                queryset.append(data)
        queryset = sorted(queryset)
        return queryset


class GetUserAssetPermissionActionsApi(RetrieveAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ActionsSerializer

    def get_object(self):
        user_id = self.request.query_params.get('user_id', '')
        asset_id = self.request.query_params.get('asset_id', '')
        system_id = self.request.query_params.get('system_user_id', '')

        try:
            user_id = uuid.UUID(user_id)
            asset_id = uuid.UUID(asset_id)
            system_id = uuid.UUID(system_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        util = AssetPermissionUtilV2(user)
        system_users_actions = util.get_asset_system_users_with_actions(asset)
        actions = system_users_actions.get(system_user)
        return {"actions": actions}


class ValidateUserAssetPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    
    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')
        action_name = request.query_params.get('action_name', '')
        cache_policy = self.request.query_params.get("cache_policy", '0')

        try:
            user_id = uuid.UUID(user_id)
            asset_id = uuid.UUID(asset_id)
            system_id = uuid.UUID(system_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        util = AssetPermissionUtilV2(user)
        system_users_actions = util.get_asset_system_users_with_actions(asset)
        actions = system_users_actions.get(system_user)
        if action_name in Action.value_to_choices(actions):
            return Response({'msg': True}, status=200)
        return Response({'msg': False}, status=403)


class RefreshAssetPermissionCacheApi(RetrieveAPIView):
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        # expire all cache
        # AssetPermissionUtil.expire_all_cache()
        return Response({'msg': True}, status=200)


class UserGrantedAssetSystemUsersApi(UserPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetSystemUserSerializer
    only_fields = serializers.AssetSystemUserSerializer.Meta.only_fields

    def get_queryset(self):
        util = AssetPermissionUtilV2(self.obj)
        asset_id = self.kwargs.get('asset_id')
        asset = get_object_or_404(Asset, id=asset_id)
        system_users_with_actions = util.get_asset_system_users_with_actions(asset)
        system_users = []
        for system_user, actions in system_users_with_actions.items():
            system_user.actions = actions
            system_users.append(system_user)
        system_users.sort(key=lambda x: x.priority)
        return system_users
