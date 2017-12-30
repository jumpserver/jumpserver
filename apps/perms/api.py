# ~*~ coding: utf-8 ~*~
# 

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import ListAPIView, get_object_or_404, RetrieveUpdateAPIView
from rest_framework import viewsets

from common.utils import get_object_or_none
from users.permissions import IsValidUser, IsSuperUser, IsAppUser, IsSuperUserOrAppUser
from .utils import get_user_granted_assets, get_user_granted_asset_groups, \
    get_user_asset_permissions, get_user_group_asset_permissions, \
    get_user_group_granted_assets, get_user_group_granted_asset_groups
from .models import AssetPermission
from .hands import AssetGrantedSerializer, User, UserGroup, AssetGroup, Asset, \
    AssetGroup, AssetGroupGrantedSerializer, SystemUser, MyAssetGroupGrantedSerializer
from . import serializers


class AssetPermissionViewSet(viewsets.ModelViewSet):
    """
    资产授权列表的增删改查api
    """
    queryset = AssetPermission.objects.all()
    serializer_class = serializers.AssetPermissionSerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        queryset = super(AssetPermissionViewSet, self).get_queryset()
        user_id = self.request.query_params.get('user', '')
        user_group_id = self.request.query_params.get('user_group', '')

        if user_id and user_id.isdigit():
            user = get_object_or_404(User, id=int(user_id))
            queryset = get_user_asset_permissions(user)

        if user_group_id:
            user_group = get_object_or_404(UserGroup, id=user_group_id)
            queryset = get_user_group_asset_permissions(user_group)
        return queryset

    def get_serializer_class(self):
        if getattr(self, 'user_id', ''):
            return serializers.UserAssetPermissionSerializer
        return serializers.AssetPermissionSerializer


class AssetPermissionRemoveUserApi(RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    permission_classes = (IsSuperUser,)
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
    permission_classes = (IsSuperUser,)
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
    permission_classes = (IsSuperUser,)
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
    permission_classes = (IsSuperUser,)
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
            for k, v in get_user_granted_assets(user).items():
                k.system_users_granted = v
                queryset.append(k)
        return queryset


class UserGrantedAssetGroupsApi(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        asset_groups = {}
        user_id = kwargs.get('pk', '')
        user = get_object_or_404(User, id=user_id)

        assets = get_user_granted_assets(user)
        for asset in assets:
            for asset_group in asset.groups.all():
                if asset_group.id in asset_groups:
                    asset_groups[asset_group.id]['assets_amount'] += 1
                else:
                    asset_groups[asset_group.id] = {
                        'id': asset_group.id,
                        'name': asset_group.name,
                        'comment': asset_group.comment,
                        'assets_amount': 1
                    }
        asset_groups_json = asset_groups.values()
        return Response(asset_groups_json, status=200)


class UserGrantedAssetGroupsWithAssetsApi(ListAPIView):
    """
    授权用户的资产组，注：这里的资产组并非是授权列表中授权的，
    而是把所有资产取出来，然后反查出所有资产组，然后合并得到，
    结果里也包含资产组下授权的资产
    数据结构如下：
    [
      {
        "id": 1,
        "name": "资产组1",
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
    serializer_class = AssetGroupGrantedSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')
        if not user_id:
            return []

        user = get_object_or_404(User, id=user_id)
        asset_groups = get_user_granted_asset_groups(user)

        queryset = []
        for asset_group, assets_system_users in asset_groups.items():
            assets = []
            for asset, system_users in assets_system_users:
                asset.system_users_granted = system_users
                assets.append(asset)
            asset_group.assets_granted = assets
            queryset.append(asset_group)
        return queryset


class MyGrantedAssetsApi(ListAPIView):
    """
    用户自己查询授权的资产列表
    """
    permission_classes = (IsValidUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        queryset = []
        user = self.request.user
        if user:
            for asset, system_users in get_user_granted_assets(user).items():
                asset.system_users_granted = system_users
                queryset.append(asset)
        return queryset


class MyGrantedAssetGroupsApi(APIView):
    """
    授权的所有资产组，并非是授权列表中的，而是经过计算得来的
    """
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        asset_groups = {}
        user = request.user

        if user:
            assets = get_user_granted_assets(user)
            for asset in assets:
                for asset_group in asset.groups.all():
                    if asset_group.id in asset_groups:
                        asset_groups[asset_group.id]['assets_amount'] += 1
                    else:
                        asset_groups[asset_group.id] = {
                            'id': asset_group.id,
                            'name': asset_group.name,
                            'comment': asset_group.comment,
                            'assets_amount': 1
                        }
        asset_groups_json = asset_groups.values()
        return Response(asset_groups_json, status=200)


class MyGrantedAssetGroupsWithAssetsApi(ListAPIView):
    """
    授权当前用户的资产组，注：这里的资产组并非是授权列表中授权的，
    而是把所有资产取出来，然后反查出所有资产组，然后合并得到，
    结果里也包含资产组下授权的资产
    数据结构如下：
    [
      {
        "id": 1,
        "name": "资产组1",
        ... 其它属性
        "assets_granted": [
          {
            "id": 1,
            "hostname": "testserver",
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
    permission_classes = (IsValidUser,)
    serializer_class = MyAssetGroupGrantedSerializer

    def get_queryset(self):
        user = self.request.user
        asset_groups = get_user_granted_asset_groups(user)

        queryset = []
        for asset_group, assets_system_users in asset_groups.items():
            assets = []
            for asset, system_users in assets_system_users:
                asset.system_users_granted = system_users
                assets.append(asset)
            asset_group.assets_granted = assets
            queryset.append(asset_group)
        return queryset


class MyAssetGroupOfAssetsApi(ListAPIView):
    """授权用户资产组下的资产列表, 非该资产组的所有资产,而是被授权的"""
    permission_classes = (IsValidUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        queryset = []
        asset_group_id = self.kwargs.get('pk', -1)
        user = self.request.user
        asset_group = get_object_or_none(AssetGroup, id=asset_group_id)

        if user and asset_group:
            assets = get_user_granted_assets(user)
            for asset in asset_group.assets.all():
                if asset in assets:
                    asset.system_users_granted = assets[asset]
                    queryset.append(asset)
        return queryset


class UserGroupGrantedAssetsApi(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')

        if user_group_id:
            user_group = get_object_or_404(UserGroup, id=user_group_id)
            queryset = get_user_group_granted_assets(user_group)
        else:
            queryset = []
        return queryset


class UserGroupGrantedAssetGroupsApi(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = AssetGroupGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')

        if user_group_id:
            user_group = get_object_or_404(UserGroup, id=user_group_id)
            queryset = get_user_group_granted_asset_groups(user_group)
        else:
            queryset = []
        return queryset


class ValidateUserAssetPermissionView(APIView):
    permission_classes = (IsAppUser,)

    @staticmethod
    def get(request):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        assets_granted = get_user_granted_assets(user)
        if system_user in assets_granted.get(asset, []):
            return Response({'msg': True}, status=200)
        else:
            return Response({'msg': False}, status=403)
