# ~*~ coding: utf-8 ~*~
# 

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework import viewsets
from users.permissions import IsValidUser, IsSuperUser, IsAppUser, IsSuperUserOrAppUser
from common.utils import get_object_or_none
from .utils import get_user_granted_assets, get_user_granted_asset_groups, \
    get_user_asset_permissions, get_user_group_asset_permissions, \
    get_user_group_granted_assets, get_user_group_granted_asset_groups
from .models import AssetPermission
from .hands import AssetGrantedSerializer, User, UserGroup, AssetGroup, Asset, \
    AssetGroup, AssetGroupSerializer, SystemUser
from . import serializers
from .utils import associate_system_users_and_assets


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

    # Todo: 忘记为何要重写get_serializer_class了
    def get_serializer_class(self):
        if getattr(self, 'user_id', ''):
            return serializers.UserAssetPermissionSerializer
        return serializers.AssetPermissionSerializer

    def associate_system_users_and_assets(self, serializer):
        assets = serializer.validated_data.get('assets', [])
        asset_groups = serializer.validated_data.get('asset_groups', [])
        system_users = serializer.validated_data.get('system_users', [])
        if serializer.partial:
            instance = self.get_object()
            assets.extend(list(instance.assets.all()))
            asset_groups.extend(list(instance.asset_groups.all()))
            system_users.extend(list(instance.system_users.all()))
        associate_system_users_and_assets(system_users, assets, asset_groups)

    def perform_create(self, serializer):
        self.associate_system_users_and_assets(serializer)
        return super(AssetPermissionViewSet, self).perform_create(serializer)

    def perform_update(self, serializer):
        self.associate_system_users_and_assets(serializer)
        return super(AssetPermissionViewSet, self).perform_update(serializer)


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


class RemoveSystemUserAssetPermission(APIView):
    """将系统用户从授权中移除, Detail页面会调用"""
    permission_classes = (IsSuperUser,)

    def put(self, request, *args, **kwargs):
        response = []
        asset_permission_id = kwargs.pop('pk')
        system_users_id = request.data.get('system_users')
        print(system_users_id)
        asset_permission = get_object_or_404(
            AssetPermission, id=asset_permission_id)
        if not isinstance(system_users_id, list):
            system_users_id = [system_users_id]
        for system_user_id in system_users_id:
            system_user = get_object_or_none(SystemUser, id=system_user_id)
            if system_user:
                asset_permission.system_users.remove(system_user)
                response.append(system_user.to_json())
        return Response(response, status=200)


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


class UserGrantedAssetGroupsApi(ListAPIView):
    permission_classes = (IsSuperUserOrAppUser,)
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
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        asset_groups = dict()
        asset_groups[0] = {
            'id': 0, 'name': 'ungrouped', 'assets': []
        }
        # asset_group = {
        #     1: {'id': 1, 'name': 'hello',
        #         'assets': [{
        #                        'id': 'asset_id',
        #                        'system_users': [{'id': 'system_user_id',...},]
        #                     }],
        #         'assets_id': set()}, 2: {}}
        user = request.user

        if user:
            assets = get_user_granted_assets(user)
            for asset, system_users in assets.items():
                asset_json = asset.to_json()
                asset_json['system_users'] = [su.to_json() for su in system_users]
                if not asset.groups.all():
                    asset_groups[0]['assets'].append(asset_json)
                    continue
                for asset_group in asset.groups.all():
                    if asset_group.id in asset_groups:
                        asset_groups[asset_group.id]['assets'].append(asset_json)
                    else:
                        asset_groups[asset_group.id] = {
                            'id': asset_group.id,
                            'name': asset_group.name,
                            'comment': asset_group.comment,
                            'assets': [asset_json],
                        }
        asset_groups_json = asset_groups.values()
        return Response(asset_groups_json, status=200)


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
    serializer_class = AssetGroupSerializer

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
