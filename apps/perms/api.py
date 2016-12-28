# ~*~ coding: utf-8 ~*~
# 

from rest_framework.views import APIView, Response
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework import viewsets
from users.permissions import IsValidUser, IsSuperUser
from common.utils import get_object_or_none
from .utils import get_user_granted_assets, get_user_granted_asset_groups, get_user_asset_permissions, \
    get_user_group_asset_permissions, get_user_group_granted_assets, get_user_group_granted_asset_groups
from .models import AssetPermission
from .hands import AssetGrantedSerializer, User, UserGroup, AssetGroup, Asset, AssetGroup, AssetGroupSerializer
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

        if user_id:
            user = get_object_or_404(User, id=user_id)
            queryset = get_user_granted_assets(user)
        else:
            queryset = []
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
    permission_classes = (IsValidUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user = self.request.user
        if user:
            queryset = get_user_granted_assets(user)
        else:
            queryset = []
        return queryset


class MyGrantedAssetsGroupsApi(APIView):
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