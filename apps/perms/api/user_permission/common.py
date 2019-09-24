# -*- coding: utf-8 -*-
#
import uuid

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveAPIView
)

from common.permissions import IsOrgAdminOrAppUser, IsOrgAdmin
from common.utils import get_logger
from ...utils import (
    AssetPermissionUtilV2
)
from ...hands import User, Asset, SystemUser
from ... import serializers
from ...models import Action
from .mixin import UserAssetPermissionMixin

logger = get_logger(__name__)

__all__ = [
    'RefreshAssetPermissionCacheApi',
    'UserGrantedAssetSystemUsersApi',
    'ValidateUserAssetPermissionApi',
    'GetUserAssetPermissionActionsApi',
]


class GetUserAssetPermissionActionsApi(UserAssetPermissionMixin,
                                       RetrieveAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ActionsSerializer

    def get_obj(self):
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

        system_users_actions = self.util.get_asset_system_users_with_actions(asset)
        actions = system_users_actions.get(system_user)
        return {"actions": actions}


class ValidateUserAssetPermissionApi(UserAssetPermissionMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_obj(self):
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

        system_users_actions = self.util.get_asset_system_users_with_actions(
            asset)
        actions = system_users_actions.get(system_user)
        if action_name in Action.value_to_choices(actions):
            return Response({'msg': True}, status=200)
        return Response({'msg': False}, status=403)


class RefreshAssetPermissionCacheApi(RetrieveAPIView):
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        AssetPermissionUtilV2.expire_all_user_tree_cache()
        return Response({'msg': True}, status=200)


class UserGrantedAssetSystemUsersApi(UserAssetPermissionMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AssetSystemUserSerializer
    only_fields = serializers.AssetSystemUserSerializer.Meta.only_fields

    def get_queryset(self):
        asset_id = self.kwargs.get('asset_id')
        asset = get_object_or_404(Asset, id=asset_id)
        system_users_with_actions = self.util.get_asset_system_users_with_actions(asset)
        system_users = []
        for system_user, actions in system_users_with_actions.items():
            system_user.actions = actions
            system_users.append(system_user)
        system_users.sort(key=lambda x: x.priority)
        return system_users
