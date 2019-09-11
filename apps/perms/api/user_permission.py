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
from ..hands import User, Asset, Node, SystemUser, NodeSerializer
from .. import serializers
from ..models import Action


logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetsApi',
    'UserGrantedAssetsAsTreeApi',
    'UserGrantedNodeAssetsApi',
    'UserGrantedNodesApi',
    'UserGrantedNodesAsTreeApi',
    'UserGrantedNodesWithAssetsAsTreeApi',
    'UserGrantedNodeChildrenApi',
    'UserGrantedNodeChildrenAsTreeApi',
    'UserGrantedNodeChildrenWithAssetsAsTreeApi',
    'RefreshAssetPermissionCacheApi',
    'UserGrantedAssetSystemUsersApi',
    'ValidateUserAssetPermissionApi',
    'GetUserAssetPermissionActionsApi',
]


class UserPermissionMixin:
    permission_classes = (IsOrgAdminOrAppUser,)
    obj = None

    def initial(self, *args, **kwargs):
        super().initial(*args, *kwargs)
        self.obj = self.get_obj()

    def get(self, request, *args, **kwargs):
        set_to_root_org()
        return super().get(request, *args, **kwargs)

    def get_obj(self):
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


class UserAssetPermissionMixin(UserPermissionMixin):
    util = None

    def initial(self, *args, **kwargs):
        super().initial(*args, *kwargs)
        cache_policy = self.request.query_params.get('cache_policy', '0')
        self.util = AssetPermissionUtilV2(self.obj, cache_policy=cache_policy)


class UserNodeTreeMixin:
    serializer_class = TreeNodeSerializer
    nodes_only_fields = ParserNode.nodes_only_fields
    tree = None

    def parse_nodes_to_queryset(self, nodes):
        nodes = nodes.only(*self.nodes_only_fields)
        _queryset = []

        tree = self.util.get_user_tree()
        for node in nodes:
            assets_amount = tree.assets_amount(node.key)
            if assets_amount == 0:
                continue
            node._assets_amount = assets_amount
            data = ParserNode.parse_node_to_tree_node(node)
            _queryset.append(data)
        return _queryset

    def get_serializer_queryset(self, queryset):
        queryset = self.parse_nodes_to_queryset(queryset)
        return queryset

    def get_serializer(self, queryset, many=True, **kwargs):
        queryset = self.get_serializer_queryset(queryset)
        queryset.sort()
        return super().get_serializer(queryset, many=many, **kwargs)


class UserAssetTreeMixin:
    serializer_class = TreeNodeSerializer
    nodes_only_fields = ParserNode.assets_only_fields

    @staticmethod
    def parse_assets_to_queryset(assets, node):
        _queryset = []
        for asset in assets:
            data = ParserNode.parse_asset_to_tree_node(node, asset)
            _queryset.append(data)
        return _queryset

    def get_serializer_queryset(self, queryset):
        queryset = queryset.only(*self.nodes_only_fields)
        _queryset = self.parse_assets_to_queryset(queryset, None)
        return _queryset

    def get_serializer(self, queryset, many=True, **kwargs):
        queryset = self.get_serializer_queryset(queryset)
        queryset.sort()
        return super().get_serializer(queryset, many=many, **kwargs)


class UserGrantedAssetsApi(UserAssetPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

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
        queryset = self.util.get_assets().only(*self.only_fields)
        return queryset


class UserGrantedAssetsAsTreeApi(UserAssetTreeMixin, UserGrantedAssetsApi):
    pass


class UserGrantedNodeAssetsApi(UserGrantedAssetsApi):
    def get_queryset(self):
        node_id = self.kwargs.get("node_id")
        node = get_object_or_404(Node, pk=node_id)
        deep = self.request.query_params.get("all", "0") == "1"
        queryset = self.util.get_nodes_assets(node, deep=deep)\
            .only(*self.only_fields)
        return queryset


class UserGrantedNodesApi(UserAssetPermissionMixin, ListAPIView):
    """
    查询用户授权的所有节点的API
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.NodeGrantedSerializer
    nodes_only_fields = NodeSerializer.Meta.only_fields

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["tree"] = self.util.user_tree
        return context

    def get_queryset(self):
        node_keys = self.util.get_nodes()
        queryset = Node.objects.filter(key__in=node_keys)\
            .only(*self.nodes_only_fields)
        return queryset


class UserGrantedNodesAsTreeApi(UserNodeTreeMixin, UserGrantedNodesApi):
    pass


class UserGrantedNodesWithAssetsAsTreeApi(UserGrantedNodesAsTreeApi):
    def get_serializer_queryset(self, queryset):
        _queryset = super().get_serializer_queryset(queryset)
        for node in queryset:
            assets = self.util.get_nodes_assets(node)
            _queryset.extend(
                UserAssetTreeMixin.parse_assets_to_queryset(assets, node)
            )
        return _queryset


class UserGrantedNodeChildrenApi(UserGrantedNodesApi):
    node = None
    tree = None
    root_keys = None  # 如果是第一次访问，则需要把二级节点添加进去，这个 roots_keys

    def get(self, request, *args, **kwargs):
        key = self.request.query_params.get("key")
        pk = self.request.query_params.get("id")
        system_user_id = self.request.query_params.get("system_user")
        if system_user_id:
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


class UserGrantedNodeChildrenAsTreeApi(UserNodeTreeMixin, UserGrantedNodeChildrenApi):
    pass


class UserGrantedNodeChildrenWithAssetsAsTreeApi(UserGrantedNodeChildrenAsTreeApi):
    nodes_only_fields = ParserNode.nodes_only_fields
    assets_only_fields = ParserNode.assets_only_fields

    def get_serializer_queryset(self, queryset):
        _queryset = super().get_serializer_queryset(queryset)
        nodes = []
        if self.node:
            nodes.append(self.node)
        elif self.root_keys:
            nodes = Node.objects.filter(key__in=self.root_keys)

        for node in nodes:
            assets = self.util.get_nodes_assets(node).only(
                *self.assets_only_fields
            )
            _queryset.extend(
                UserAssetTreeMixin.parse_assets_to_queryset(assets, node)
            )
        return _queryset


class GetUserAssetPermissionActionsApi(UserAssetPermissionMixin, RetrieveAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ActionsSerializer

    def get_obj(self):
        user_id = self.request.query_params.get('user_id', '')
        user = get_object_or_404(User, id=user_id)
        return user

    def get_object(self):
        asset_id = self.request.query_params.get('asset_id', '')
        system_id = self.request.query_params.get('system_user_id', '')

        try:
            asset_id = uuid.UUID(asset_id)
            system_id = uuid.UUID(system_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        system_users_actions = self.util.get_asset_system_users_with_actions(asset)
        actions = system_users_actions.get(system_user)
        return {"actions": actions}


class ValidateUserAssetPermissionApi(UserAssetPermissionMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_obj(self):
        user_id = self.request.query_params.get('user_id', '')
        user = get_object_or_404(User, id=user_id)
        return user
    
    def get(self, request, *args, **kwargs):
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')
        action_name = request.query_params.get('action_name', '')

        try:
            asset_id = uuid.UUID(asset_id)
            system_id = uuid.UUID(system_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        system_users_actions = self.util.get_asset_system_users_with_actions(asset)
        actions = system_users_actions.get(system_user)
        if action_name in Action.value_to_choices(actions):
            return Response({'msg': True}, status=200)
        return Response({'msg': False}, status=403)


class RefreshAssetPermissionCacheApi(RetrieveAPIView):
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        AssetPermissionUtilV2.expire_all_user_tree_cache()
        return Response({'msg': True}, status=200)


class UserGrantedAssetSystemUsersApi(UserAssetPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetSystemUserSerializer
    only_fields = serializers.AssetSystemUserSerializer.Meta.only_fields

    def get_queryset(self):
        asset_id = self.kwargs.get('asset_id')
        asset = get_object_or_404(Asset, id=asset_id)
        system_users_with_actions = self.util.get_asset_system_users_with_actions(asset)
        system_users = []
        for system_user, actions in system_users_with_actions.items():
            system_user.actions = actions
            system_users.append(system_user)
        system_users.sort(key=lambda x: x.priority)
        return system_users
