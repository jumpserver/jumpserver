# ~*~ coding: utf-8 ~*~
# 

from rest_framework.views import APIView, Response
from rest_framework.generics import ListCreateAPIView
from users.backends import IsValidUser, IsSuperUser
from .utils import get_user_granted_assets, get_user_granted_asset_groups
from .models import AssetPermission
from . import serializers


class AssetPermissionListCreateApi(ListCreateAPIView):
    queryset = AssetPermission.objects.all()
    serializer_class = serializers.AssetPermissionSerializer
    permission_classes = (IsSuperUser,)


class UserAssetsGrantedApi(APIView):
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


class UserAssetsGroupsGrantedApi(APIView):
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
                            'asset_num': 1
                        }

        asset_groups_json = asset_groups.values()
        return Response(asset_groups_json, status=200)