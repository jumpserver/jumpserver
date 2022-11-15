from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView, get_object_or_404

<<<<<<< HEAD
from common.utils import get_logger, lazyproperty
=======
from common.exceptions import JMSObjectDoesNotExist
from common.utils import get_logger, lazyproperty, is_uuid
>>>>>>> 0d3c5dddf9c838c5dcd28c20b6a8498088e45ce2
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

    @lazyproperty
<<<<<<< HEAD
=======
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
>>>>>>> 0d3c5dddf9c838c5dcd28c20b6a8498088e45ce2
    def asset(self):
        asset_id = self.kwargs.get('asset_id')
        kwargs = {'id': asset_id, 'is_active': True}
        asset = get_object_or_404(Asset, **kwargs)
        return asset

    def get_queryset(self):
        util = PermAccountUtil()
        accounts = util.get_permed_accounts_for_user(self.user, self.asset)
        return accounts
