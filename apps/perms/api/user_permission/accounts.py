from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, get_object_or_404

from common.permissions import IsValidUser
from common.utils import get_logger, lazyproperty
from perms import serializers
from perms.hands import User, Asset
from perms.utils import PermAccountUtil

logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetAccountsApi',
    'MyGrantedAssetAccountsApi',
]


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
        util = PermAccountUtil()
        accounts = util.get_permed_accounts_for_user(self.user, self.asset)
        return accounts


class MyGrantedAssetAccountsApi(UserGrantedAssetAccountsApi):
    permission_classes = (IsValidUser,)

    @lazyproperty
    def user(self):
        return self.request.user
