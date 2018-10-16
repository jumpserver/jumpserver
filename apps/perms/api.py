# ~*~ coding: utf-8 ~*~
# 

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import ListAPIView, get_object_or_404, RetrieveUpdateAPIView
from rest_framework import viewsets

from common.utils import set_or_append_attr_bulk
from common.permissions import IsValidUser, IsOrgAdmin, IsOrgAdminOrAppUser
from orgs.mixins import RootOrgViewMixin
from .utils import AssetPermissionUtil
from .models import AssetPermission
from .hands import AssetGrantedSerializer, User, UserGroup, Asset, Node, \
    NodeGrantedSerializer, SystemUser, NodeSerializer
from orgs.utils import set_to_root_org
from . import serializers


class AssetPermissionViewSet(viewsets.ModelViewSet):
    """
    资产授权列表的增删改查api
    """
    queryset = AssetPermission.objects.all()
    serializer_class = serializers.AssetPermissionCreateUpdateSerializer
    permission_classes = (IsOrgAdmin,)

    def get_serializer_class(self):
        if self.action in ("list", 'retrieve'):
            return serializers.AssetPermissionListSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.query_params.get('asset')
        node_id = self.request.query_params.get('node')
        inherit_nodes = set()
        if not asset_id and not node_id:
            return queryset

        permissions = set()
        if asset_id:
            asset = get_object_or_404(Asset, pk=asset_id)
            permissions = set(queryset.filter(assets=asset))
            for node in asset.nodes.all():
                inherit_nodes.update(set(node.get_ancestor(with_self=True)))
        elif node_id:
            node = get_object_or_404(Node, pk=node_id)
            permissions = set(queryset.filter(nodes=node))
            inherit_nodes = node.get_ancestor()

        for n in inherit_nodes:
            _permissions = queryset.filter(nodes=n)
            set_or_append_attr_bulk(_permissions, "inherit", n.value)
            permissions.update(_permissions)
        return permissions


class UserGrantedAssetsApi(ListAPIView):
    """
    用户授权的所有资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    
    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()
    
    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        queryset = []

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user

        util = AssetPermissionUtil(user)
        for k, v in util.get_assets().items():
            system_users_granted = [s for s in v if s.protocol == k.protocol]
            k.system_users_granted = system_users_granted
            queryset.append(k)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesApi(ListAPIView):
    """
    查询用户授权的所有节点的API, 如果是超级用户或者是 app，切换到root org
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = NodeSerializer
    
    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        util = AssetPermissionUtil(user)
        nodes = util.get_nodes_with_assets()
        return nodes.keys()

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesWithAssetsApi(ListAPIView):
    """
    用户授权的节点并带着节点下资产的api
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = NodeGrantedSerializer
    
    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        queryset = []
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)

        util = AssetPermissionUtil(user)
        nodes = util.get_nodes_with_assets()
        for node, _assets in nodes.items():
            assets = _assets.keys()
            for k, v in _assets.items():
                system_users_granted = [s for s in v if s.protocol == k.protocol]
                k.system_users_granted = system_users_granted
            node.assets_granted = assets
            queryset.append(node)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodeAssetsApi(ListAPIView):
    """
    查询用户授权的节点下的资产的api, 与上面api不同的是，只返回某个节点下的资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    
    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        node_id = self.kwargs.get('node_id')

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        util = AssetPermissionUtil(user)
        node = get_object_or_404(Node, id=node_id)
        nodes = util.get_nodes_with_assets()
        assets = nodes.get(node, [])
        for asset, system_users in assets.items():
            asset.system_users_granted = system_users
        return assets

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


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
    serializer_class = NodeGrantedSerializer

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


class UserGroupGrantedNodeAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        node_id = self.kwargs.get('node_id')

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        node = get_object_or_404(Node, id=node_id)
        util = AssetPermissionUtil(user_group)
        nodes = util.get_nodes_with_assets()
        assets = nodes.get(node, [])
        for asset, system_users in assets.items():
            asset.system_users_granted = system_users
        return assets


class ValidateUserAssetPermissionView(RootOrgViewMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    @staticmethod
    def get(request):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        util = AssetPermissionUtil(user)
        assets_granted = util.get_assets()
        if system_user in assets_granted.get(asset, []):
            return Response({'msg': True}, status=200)
        else:
            return Response({'msg': False}, status=403)


class AssetPermissionRemoveUserApi(RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.remove(*tuple(users))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddUserApi(RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.add(*tuple(users))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionRemoveAssetApi(RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.remove(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddAssetApi(RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.add(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})
