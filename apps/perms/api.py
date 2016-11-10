# ~*~ coding: utf-8 ~*~
# 

from rest_framework.views import APIView, Response
from rest_framework.generics import ListAPIView
from rest_framework import viewsets
from users.backends import IsValidUser, IsSuperUser
from common.utils import get_object_or_none
from .utils import get_user_granted_assets, get_user_granted_asset_groups, get_user_asset_permissions
from .models import AssetPermission
from .hands import AssetGrantedSerializer, User, AssetGroup, Asset, AssetGroup
from . import serializers


class AssetPermissionViewSet(viewsets.ModelViewSet):
    queryset = AssetPermission.objects.all()
    serializer_class = serializers.AssetPermissionSerializer
    permission_classes = (IsSuperUser,)

    def get_queryset(self):
        queryset = super(AssetPermissionViewSet, self).get_queryset()
        user_id = self.request.query_params.get('user', '')
        if user_id and user_id.isdigit():
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
            asset_permission = get_object_or_none(AssetPermission, id=int(permission_id))
            user = get_object_or_none(User, id=int(user_id))

            if asset_permission and user:
                asset_permission.users.remove(user)
                return Response({'msg': 'success'})
        return Response({'msg': 'failed'}, status=404)


class UserAssetsApi(ListAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user = self.request.user
        if user:
            queryset = get_user_granted_assets(user)
            return queryset
        return []


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
                        asset_groups[asset_group.id]['asset_amount'] += 1
                    else:
                        asset_groups[asset_group.id] = {
                            'id': asset_group.id,
                            'name': asset_group.name,
                            'comment': asset_group.comment,
                            'asset_amount': 1
                        }
        asset_groups_json = asset_groups.values()
        return Response(asset_groups_json, status=200)


class UserAssetsGroupAssetsApi(ListAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        queryset = []
        asset_group_id = self.kwargs.get('pk', -1)
        user = self.request.user
        asset_group = get_object_or_none(AssetGroup, id=asset_group_id)

        if user and asset_group:
            assets = get_user_granted_assets(user)
            for asset in assets:
                if asset_group in asset.groups.all():
                    queryset.append(asset)
        return queryset
