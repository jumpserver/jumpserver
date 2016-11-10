# ~*~ coding: utf-8 ~*~
# 

from rest_framework.views import APIView, Response
from rest_framework.generics import ListCreateAPIView
from rest_framework import viewsets
from users.backends import IsValidUser, IsSuperUser
from common.utils import get_object_or_none
from .utils import get_user_granted_assets, get_user_granted_asset_groups, get_user_asset_permissions
from .models import AssetPermission
from .hands import User
from . import serializers


class AssetPermissionViewSet(viewsets.ModelViewSet):
    queryset = AssetPermission.objects.all()
    serializer_class = serializers.AssetPermissionSerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        queryset = super(AssetPermissionViewSet, self).get_queryset()
        user_id = self.request.query_params.get('user', '')
        if user_id and user_id.isdigit():
            from users.models import User
            self.user_id = user_id
            user = get_object_or_none(User, id=int(user_id))
            if user:
                queryset = get_user_asset_permissions(user)
                print(queryset)
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
            permission_id = int(permission_id)
            user_id = int(user_id)
            asset_permission = get_object_or_none(AssetPermission, id=permission_id)
            user = get_object_or_none(User, id=user_id)
            print(asset_permission)
            print(user)

            if asset_permission and user:
                asset_permission.users.remove(user)
                return Response({'msg': 'success'})
        return Response({'msg': 'failed'}, status=404)


class UserAssetsApi(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        assets_json = []
        user = request.user

        if user:
            assets = get_user_granted_assets(user)

            for asset, system_users in assets.items():
                assets_json.append({
                    'id': asset.id,
                    'hostname': asset.hostname,
                    'ip': asset.ip,
                    'port': asset.port,
                    'system_users': [
                        {
                            'id': system_user.id,
                            'name': system_user.name,
                            'username': system_user.username,
                        } for system_user in system_users
                    ],
                    'comment': asset.comment
                })

        return Response(assets_json, status=200)


class UserAssetsGroupsApi(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        asset_groups = {}
        user = request.user

        if user:
            assets = get_user_granted_assets(user)
            for asset in assets:
                for asset_group in asset.groups.all():
                    if asset_group.id in asset_groups:
                        asset_groups[asset_group.id]['asset_num'] += 1
                    else:
                        asset_groups[asset_group.id] = {
                            'id': asset_group.id,
                            'name': asset_group.name,
                            'comment': asset_group.comment,
                            'asset_num': 1
                        }

        asset_groups_json = asset_groups.values()
        return Response(asset_groups_json, status=200)


class UserAssetsGroupAssetsApi(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        # asset_group_id = request.query_params.get('asset_group_id', -1)
        asset_group_id = kwargs.get('pk', -1)
        # asset_group_name = request.query_params.get('asset_group_name', '')
        user = request.user
        assets_json = []

        if user:
            assets = get_user_granted_assets(user)
            for asset, system_users in assets.items():
                for asset_group in asset.groups.all():
                    if str(asset_group.id) == asset_group_id: # and asset_group.name == asset_group_name:
                        assets_json.append({
                            'id': asset.id,
                            'hostname': asset.hostname,
                            'ip': asset.ip,
                            'port': asset.port,
                            'system_users': [
                                {
                                    'id': system_user.id,
                                    'name': system_user.name,
                                    'username': system_user.username,
                                } for system_user in system_users
                                ],
                            'comment': asset.comment
                        })
        return Response(assets_json, status=200)
