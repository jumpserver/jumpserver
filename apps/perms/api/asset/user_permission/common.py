# -*- coding: utf-8 -*-
#
import uuid

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveAPIView, DestroyAPIView
)

from orgs.utils import tmp_to_root_org
from perms.utils.asset.permission import get_asset_system_users_id_with_actions_by_user
from common.permissions import IsOrgAdminOrAppUser, IsOrgAdmin, IsValidUser
from common.utils import get_logger, lazyproperty

from perms.hands import User, Asset, SystemUser
from perms import serializers
from perms.models import Action

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

        system_users_actions = get_asset_system_users_id_with_actions_by_user(self.get_user(), asset)
        actions = system_users_actions.get(system_user.id)
        return {"actions": actions}


@method_decorator(tmp_to_root_org(), name='get')
class ValidateUserAssetPermissionApi(APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_cache_policy(self):
        return 0

    def get_user(self):
        user_id = self.request.query_params.get('user_id', '')
        user = get_object_or_404(User, id=user_id)
        return user

    def get(self, request, *args, **kwargs):
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')
        action_name = request.query_params.get('action_name', '')

        try:
            asset_id = uuid.UUID(asset_id)
            system_id = uuid.UUID(system_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        system_users_actions = get_asset_system_users_id_with_actions_by_user(self.get_user(), asset)
        actions = system_users_actions.get(system_user.id)
        if actions is None:
            return Response({'msg': False}, status=403)
        if action_name in Action.value_to_choices(actions):
            return Response({'msg': True}, status=200)
        return Response({'msg': False}, status=403)


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

    def get_asset_system_users_id_with_actions(self, asset):
        return get_asset_system_users_id_with_actions_by_user(self.user, asset)

    def get_queryset(self):
        asset_id = self.kwargs.get('asset_id')
        asset = get_object_or_404(Asset, id=asset_id)
        system_users_with_actions = self.get_asset_system_users_id_with_actions(asset)
        system_users_id = system_users_with_actions.keys()
        system_users = SystemUser.objects.filter(id__in=system_users_id)\
            .only(*self.serializer_class.Meta.only_fields) \
            .order_by('priority')
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
