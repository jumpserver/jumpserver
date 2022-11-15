from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, get_object_or_404

from common.utils import get_logger
from perms import serializers
from perms.hands import Asset
from perms.utils import PermAccountUtil
from .mixin import SelfOrPKUserMixin

logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetAccountsApi',
]


class UserGrantedAssetAccountsApi(SelfOrPKUserMixin, ListAPIView):
    serializer_class = serializers.AccountsGrantedSerializer
    rbac_perms = (
        ('GET', 'perms.view_userassets'),
        ('list', 'perms.view_userassets'),
    )

    def asset(self):
        asset_id = self.kwargs.get('asset_id')
        kwargs = {'id': asset_id, 'is_active': True}
        asset = get_object_or_404(Asset, **kwargs)
        return asset

    def get_queryset(self):
        util = PermAccountUtil()
        accounts = util.get_permed_accounts_for_user(self.user, self.asset)
        return accounts
