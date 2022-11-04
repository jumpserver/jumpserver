from rest_framework import generics
from assets.serializers import AccountSerializer
from perms.utils.account import PermAccountUtil
from .mixin import RoleAdminMixin, RoleUserMixin


__all__ = ['UserAllGrantedAccountsApi', 'MyAllGrantedAccountsApi']


class UserAllGrantedAccountsApi(RoleAdminMixin, generics.ListAPIView):
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
