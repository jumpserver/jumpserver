# ~*~ coding: utf-8 ~*~
# 

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework import viewsets

from users.permissions import IsValidUser, IsSuperUser, IsSuperUserOrAppUser
from .utils import NodePermissionUtil
from .models import NodePermission
from .hands import AssetGrantedSerializer, User, UserGroup, Asset, \
    NodeGrantedSerializer, SystemUser, NodeSerializer
from . import serializers


class AssetPermissionViewSet(viewsets.ModelViewSet):
    """
    资产授权列表的增删改查api
    """
    queryset = NodePermission.objects.all()
    serializer_class = serializers.AssetPermissionCreateUpdateSerializer
    permission_classes = (IsSuperUser,)

    def get_serializer_class(self):
        if self.action in ("list", 'retrieve'):
            return serializers.AssetPermissionListSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = super().get_queryset()
        node_id = self.request.query_params.get('node_id')

        if node_id:
            queryset = queryset.filter(node__id=node_id)

        return queryset


class UserGrantedAssetsApi(ListAPIView):
    """
    用户授权的所有资产
    """
    permission_classes = (IsSuperUserOrAppUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        queryset = []

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user

        for k, v in NodePermissionUtil.get_user_assets(user).items():
            if k.is_unixlike():
                system_users_granted = [s for s in v if s.protocol == 'ssh']
            else:
                system_users_granted = [s for s in v if s.protocol == 'rdp']
            k.system_users_granted = system_users_granted
            queryset.append(k)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesApi(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = NodeSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        nodes = NodePermissionUtil.get_user_nodes(user)
        return nodes.keys()


class UserGrantedNodesWithAssetsApi(ListAPIView):
    """
    授权用户的资产组，注：这里的资产组并非是授权列表中授权的，
    而是把所有资产取出来，然后反查出所有资产组，然后合并得到，
    结果里也包含资产组下授权的资产
    数据结构如下：
    [
      {
        "id": 1,
        "value": "node",
        ... 其它属性
        "assets_granted": [
          {
            "id": 1,
            "hostname": "testserver",
            "ip": "192.168.1.1",
            "port": 22,
            "system_users_granted": [
              "id": 1,
              "name": "web",
              "username": "web",
              "protocol": "ssh",
            ]
          }
        ]
      }
    ]
    """
    permission_classes = (IsSuperUserOrAppUser,)
    serializer_class = NodeGrantedSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        queryset = []
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)

        nodes = NodePermissionUtil.get_user_nodes_with_assets(user)
        assets = {}
        for k, v in NodePermissionUtil.get_user_assets(user).items():
            if k.is_unixlike():
                system_users_granted = [s for s in v if s.protocol == 'ssh']
            else:
                system_users_granted = [s for s in v if s.protocol == 'rdp']
            assets[k] = system_users_granted
        for node, v in nodes.items():
            for asset in v['assets']:
                asset.system_users_granted = assets[asset]
            node.assets_granted = v['assets']
            queryset.append(node)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGroupGrantedAssetsApi(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = []

        if not user_group_id:
            return queryset

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        assets = NodePermissionUtil.get_user_group_assets(user_group)
        for k, v in assets.items():
            k.system_users_granted = v
            queryset.append(k)
        return queryset


class UserGroupGrantedNodesApi(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = NodeSerializer

    def get_queryset(self):
        group_id = self.kwargs.get('pk', '')
        queryset = []

        if group_id:
            group = get_object_or_404(UserGroup, id=group_id)
            nodes = NodePermissionUtil.get_user_group_nodes(group)
            queryset = nodes.keys()
        return queryset


class UserGroupGrantedNodesWithAssetsApi(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = NodeGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = []

        if not user_group_id:
            return queryset

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        nodes = NodePermissionUtil.get_user_group_nodes_with_assets(user_group)
        for node, v in nodes.items():
            for asset in v['assets']:
                asset.system_users_granted = v['system_users']
            node.assets_granted = v['assets']
            queryset.append(node)
        return queryset


class ValidateUserAssetPermissionView(APIView):
    permission_classes = (IsSuperUserOrAppUser,)

    @staticmethod
    def get(request):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        assets_granted = NodePermissionUtil.get_user_assets(user)
        if system_user in assets_granted.get(asset, []):
            return Response({'msg': True}, status=200)
        else:
            return Response({'msg': False}, status=403)
