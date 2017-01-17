# ~*~ coding: utf-8 ~*~
# 

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework import viewsets
from users.permissions import IsValidUser, IsSuperUser, IsAppUser
from common.utils import get_object_or_none
from .utils import get_user_granted_assets, get_user_granted_asset_groups, \
    get_user_asset_permissions, get_user_group_asset_permissions, \
    get_user_group_granted_assets, get_user_group_granted_asset_groups
from .models import AssetPermission
from .hands import AssetGrantedSerializer, User, UserGroup, AssetGroup, Asset, \
    AssetGroup, AssetGroupSerializer, SystemUser
from . import serializers


class AssetPermissionViewSet(viewsets.ModelViewSet):
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


class RevokeUserAssetPermission(APIView):
    permission_classes = (IsSuperUser,)

    def put(self, request, *args, **kwargs):
        permission_id = str(request.data.get('id', ''))
        user_id = str(request.data.get('user_id', ''))

        if permission_id and user_id and permission_id.isdigit() and user_id.isdigit():
            asset_permission = get_object_or_404(AssetPermission, id=int(permission_id))
            user = get_object_or_404(User, id=int(user_id))

            if asset_permission and user:
                asset_permission.users.remove(user)
                return Response({'msg': 'success'})
        return Response({'msg': 'failed'}, status=404)


class RevokeUserGroupAssetPermission(APIView):
    permission_classes = (IsSuperUser,)

    def put(self, request, *args, **kwargs):
        permission_id = str(request.data.get('id', ''))
        user_group_id = str(request.data.get('user_group_id', ''))

        if permission_id and user_group_id and permission_id.isdigit() and user_group_id.isdigit():
            asset_permission = get_object_or_404(AssetPermission, id=int(permission_id))
            user_group = get_object_or_404(UserGroup, id=int(user_group_id))

            if asset_permission and user_group:
                asset_permission.user_groups.remove(user_group)
                return Response({'msg': 'success'})
        return Response({'msg': 'failed'}, status=404)


class UserGrantedAssetsApi(ListAPIView):
    permission_classes = (IsSuperUser,)
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


class UserGrantedAssetGroupsApi(ListAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class = AssetGroupSerializer

    def get_queryset(self):
        user_id = self.kwargs.get('pk', '')

        if user_id:
            user = get_object_or_404(User, id=user_id)
            queryset = get_user_granted_asset_groups(user)
        else:
            queryset = []
        return queryset


class MyGrantedAssetsApi(ListAPIView):
    """授权给用户的资产列表
    [{'hostname': 'x','ip': 'x', ..,
      'system_users_granted': [{'name': 'x', .}, ...]
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


class MyGrantedAssetsGroupsApi(APIView):
    """授权给用户的资产组列表, 非直接通过授权规则授权的资产组列表, 而是授权资产的所有
    资产组之和"""
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


class MyAssetGroupAssetsApi(ListAPIView):
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
    serializer_class = AssetGroupSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')

        if user_group_id:
            user_group = get_object_or_404(UserGroup, id=user_group_id)
            queryset = get_user_group_granted_asset_groups(user_group)
        else:
            queryset = []
        return queryset


class CheckUserAssetSystemPermission(APIView):
    permission_classes = (IsAppUser,)

    def get(self, request):
        user_id = request.params.get('user_id', '')
        asset_id = request.params.get('asset_id', '')
        system_id = request.params.get('system_id', '')

        user = get_object_or_none(User, id=user_id)
        asset = get_object_or_none(Asset, id=asset_id)
        system_user = get_object_or_none(SystemUser, id=system_id)

        if not (user and asset and system_user):
            return Response(status=403)

        assets_granted = get_user_granted_assets(user)


