from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, get_object_or_404

from common.permissions import IsValidUser
from common.utils import get_logger, lazyproperty
from assets.serializers import AccountSerializer
from perms.hands import User, Asset, Account
from perms import serializers
from perms.utils import PermAccountUtil
from .mixin import RoleAdminMixin, RoleUserMixin

logger = get_logger(__name__)


__all__ = [
    'UserAllGrantedAccountsApi',
    'MyAllGrantedAccountsApi',
    'UserGrantedAssetAccountsApi',
    'MyGrantedAssetAccountsApi',
    'UserGrantedAssetSpecialAccountsApi',
    'MyGrantedAssetSpecialAccountsApi',
]


class UserAllGrantedAccountsApi(RoleAdminMixin, ListAPIView):
    """ 授权给用户的所有账号列表 """
    serializer_class = AccountSerializer
    filterset_fields = ("name", "username", "privileged", "version")
    search_fields = filterset_fields

    def get_queryset(self):
        util = PermAccountUtil()
        accounts = util.get_perm_accounts_for_user(self.user)
        return accounts


class MyAllGrantedAccountsApi(RoleUserMixin, UserAllGrantedAccountsApi):
    """ 授权给我的所有账号列表 """
    pass


class UserGrantedAssetAccountsApi(ListAPIView):
    serializer_class = serializers.AccountsGrantedSerializer

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

    @lazyproperty
    def user(self):
        return self.request.user

    def get_queryset(self):
        # 构造默认包含的账号，如: @INPUT @USER
        accounts = [
            Account.get_manual_account(),
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
