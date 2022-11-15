from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, get_object_or_404

from common.exceptions import JMSObjectDoesNotExist
from common.utils import get_logger, lazyproperty, is_uuid
from perms import serializers
from perms.hands import User, Asset
from perms.utils import PermAccountUtil

logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetAccountsApi',
]


class UserGrantedAssetAccountsApi(ListAPIView):
    serializer_class = serializers.AccountsGrantedSerializer
    rbac_perms = (
        ('GET', 'perms.view_userassets'),
        ('list', 'perms.view_userassets'),
    )

    @lazyproperty
    def user(self) -> User:
        query_user = self.kwargs.get('user')
        if is_uuid(query_user):
            user = User.objects.get(id=query_user)
        elif query_user == 'my':
            user = self.request.user
        else:
            raise JMSObjectDoesNotExist(object_name=_('User'))
        return user

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
