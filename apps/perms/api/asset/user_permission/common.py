# -*- coding: utf-8 -*-
#
import uuid
import time

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework.views import APIView, Response
from rest_framework import status
from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveAPIView, DestroyAPIView
)

from orgs.utils import tmp_to_root_org
from perms.utils.asset.permission import get_asset_system_user_ids_with_actions_by_user, validate_permission
from common.permissions import IsOrgAdminOrAppUser, IsOrgAdmin, IsValidUser
from common.utils import get_logger, lazyproperty

from perms.hands import User, Asset, SystemUser
from perms import serializers

logger = get_logger(__name__)

__all__ = [
    'RefreshAssetPermissionCacheApi',
    'UserGrantedAssetSystemUsersForAdminApi',
    'ValidateUserAssetPermissionApi',
    'GetUserAssetPermissionActionsApi',
    'UserAssetPermissionsCacheApi',
    'MyGrantedAssetSystemUsersApi',
]


@method_decorator(tmp_to_root_org(), name='get')
class GetUserAssetPermissionActionsApi(RetrieveAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ActionsSerializer

    def get_user(self):
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

        system_users_actions = get_asset_system_user_ids_with_actions_by_user(self.get_user(), asset)
        actions = system_users_actions.get(system_user.id)
        return {"actions": actions}


@method_decorator(tmp_to_root_org(), name='get')
class ValidateUserAssetPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_cache_policy(self):
        return 0

    def get(self, request, *args, **kwargs):
        user_id = self.request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')
        action_name = request.query_params.get('action_name', '')

        if not all((user_id, asset_id, system_id, action_name)):
            return Response({'has_permission': False, 'expire_at': int(time.time())})

        user = User.objects.get(id=user_id)
        asset = Asset.objects.valid().get(id=asset_id)
        system_user = SystemUser.objects.get(id=system_id)

        has_permission, expire_at = validate_permission(user, asset, system_user, action_name)
        status_code = status.HTTP_200_OK if has_permission else status.HTTP_403_FORBIDDEN
        return Response({'has_permission': has_permission, 'expire_at': int(expire_at)}, status=status_code)


# TODO 删除
class RefreshAssetPermissionCacheApi(RetrieveAPIView):
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        return Response({'msg': True}, status=200)


class UserGrantedAssetSystemUsersForAdminApi(ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetSystemUserSerializer
    only_fields = serializers.AssetSystemUserSerializer.Meta.only_fields

    @lazyproperty
    def user(self):
        user_id = self.kwargs.get('pk')
        return User.objects.get(id=user_id)

    def get_asset_system_user_ids_with_actions(self, asset):
        return get_asset_system_user_ids_with_actions_by_user(self.user, asset)

    def get_queryset(self):
        asset_id = self.kwargs.get('asset_id')
        asset = get_object_or_404(Asset, id=asset_id, is_active=True)
        system_users_with_actions = self.get_asset_system_user_ids_with_actions(asset)
        system_user_ids = system_users_with_actions.keys()
        system_users = SystemUser.objects.filter(id__in=system_user_ids)\
            .only(*self.serializer_class.Meta.only_fields) \
            .order_by('name')
        system_users = list(system_users)
        for system_user in system_users:
            actions = system_users_with_actions.get(system_user.id, 0)
            system_user.actions = actions
        return system_users


@method_decorator(tmp_to_root_org(), name='list')
class MyGrantedAssetSystemUsersApi(UserGrantedAssetSystemUsersForAdminApi):
    permission_classes = (IsValidUser,)

    @lazyproperty
    def user(self):
        return self.request.user


# TODO 删除
class UserAssetPermissionsCacheApi(DestroyAPIView):
    permission_classes = (IsOrgAdmin,)

    def destroy(self, request, *args, **kwargs):
        return Response(status=204)
