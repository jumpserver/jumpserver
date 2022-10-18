# -*- coding: utf-8 -*-
#
import uuid
import time
from collections import defaultdict

from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from rest_framework.views import APIView, Response
from rest_framework import status
from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveAPIView
)

from orgs.utils import tmp_to_root_org
from perms.utils.permission import (
    get_asset_system_user_ids_with_actions_by_user, validate_permission
)
from common.permissions import IsValidUser
from common.utils import get_logger, lazyproperty

from perms.hands import User, Asset, Account
from perms import serializers
from perms.models import AssetPermission, Action
from perms.utils import PermAccountUtil

logger = get_logger(__name__)

__all__ = [
    'ValidateUserAssetPermissionApi',
    'GetUserAssetPermissionActionsApi',
    'UserGrantedAssetAccountsApi',
    'MyGrantedAssetAccountsApi',
    'UserGrantedAssetSpecialAccountsApi',
    'MyGrantedAssetSpecialAccountsApi',
]


@method_decorator(tmp_to_root_org(), name='get')
class GetUserAssetPermissionActionsApi(RetrieveAPIView):
    serializer_class = serializers.ActionsSerializer
    rbac_perms = {
        'retrieve': 'perms.view_userassets',
        'GET': 'perms.view_userassets',
    }

    def get_user(self):
        user_id = self.request.query_params.get('user_id', '')
        user = get_object_or_404(User, id=user_id)
        return user

    def get_object(self):
        asset_id = self.request.query_params.get('asset_id', '')
        account = self.request.query_params.get('account', '')

        try:
            asset_id = uuid.UUID(asset_id)
        except ValueError:
            return Response({'msg': False}, status=403)

        asset = get_object_or_404(Asset, id=asset_id)

        system_users_actions = get_asset_system_user_ids_with_actions_by_user(self.get_user(), asset)
        # actions = system_users_actions.get(system_user.id)
        actions = system_users_actions.get(account)
        return {"actions": actions}


@method_decorator(tmp_to_root_org(), name='get')
class ValidateUserAssetPermissionApi(APIView):
    rbac_perms = {
        'GET': 'perms.view_userassets'
    }

    def get(self, request, *args, **kwargs):
        user_id = self.request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        account = request.query_params.get('account', '')
        action_name = request.query_params.get('action_name', '')

        data = {
            'has_permission': False,
            'expire_at': int(time.time()),
            'actions': []
        }

        if not all((user_id, asset_id, account, action_name)):
            return Response(data)

        user = User.objects.get(id=user_id)
        asset = Asset.objects.valid().get(id=asset_id)

        has_perm, actions, expire_at = validate_permission(user, asset, account, action_name)
        status_code = status.HTTP_200_OK if has_perm else status.HTTP_403_FORBIDDEN
        data = {
            'has_permission': has_perm,
            'actions': actions,
            'expire_at': int(expire_at)
        }
        return Response(data, status=status_code)


class UserGrantedAssetAccountsApi(ListAPIView):
    serializer_class = serializers.AccountsGrantedSerializer
    rbac_perms = {
        'list': 'perms.view_userassets'
    }

    @lazyproperty
    def user(self) -> User:
        user_id = self.kwargs.get('pk')
        return User.objects.get(id=user_id)

    @lazyproperty
    def asset(self):
        asset_id = self.kwargs.get('asset_id')
        kwargs = {'id': asset_id, 'is_active': True}
        asset = get_object_or_404(Asset, **kwargs)
        return asset

    def get_queryset(self):
        accounts = PermAccountUtil().get_perm_accounts_for_user_asset(
            self.user, self.asset, with_actions=True
        )
        return accounts


class MyGrantedAssetAccountsApi(UserGrantedAssetAccountsApi):
    permission_classes = (IsValidUser,)

    @lazyproperty
    def user(self):
        return self.request.user


class UserGrantedAssetSpecialAccountsApi(ListAPIView):
    serializer_class = serializers.AccountsGrantedSerializer
    rbac_perms = {
        'list': 'perms.view_userassets'
    }

    @lazyproperty
    def user(self):
        return self.request.user

    def get_queryset(self):
        # 构造默认包含的账号，如: @INPUT @USER
        accounts = [
            Account.get_input_account(),
            Account.get_user_account(self.user.username)
        ]
        for account in accounts:
            account.actions = Action.ALL
        return accounts


class MyGrantedAssetSpecialAccountsApi(UserGrantedAssetSpecialAccountsApi):
    permission_classes = (IsValidUser,)

    @lazyproperty
    def user(self):
        return self.request.user
