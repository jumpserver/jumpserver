# -*- coding: utf-8 -*-
#
from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListAPIView, get_object_or_404
)
from common.permissions import IsValidUser
from common.utils import get_logger, lazyproperty

from perms.hands import User, Asset, Account
from perms import serializers
from perms.models import Action
from perms.utils import PermAccountUtil

logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetAccountsApi',
    'MyGrantedAssetAccountsApi',
    'UserGrantedAssetSpecialAccountsApi',
    'MyGrantedAssetSpecialAccountsApi',
]


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
