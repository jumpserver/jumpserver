from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from accounts import serializers
from accounts.filters import AccountFilterSet
from accounts.models import Account
from assets.models import Asset
from authentication.const import ConfirmType
from common.permissions import UserConfirmation
from common.views.mixins import RecordViewLogMixin
from orgs.mixins.api import OrgBulkModelViewSet

__all__ = [
    'AccountViewSet', 'AccountSecretsViewSet',
    'AccountHistoriesSecretAPI'
]

from rbac.permissions import RBACPermission


class AccountViewSet(OrgBulkModelViewSet):
    model = Account
    search_fields = ('username', 'asset__address', 'name')
    filterset_class = AccountFilterSet
    serializer_classes = {
        'default': serializers.AccountSerializer,
    }
    rbac_perms = {
        'partial_update': ['accounts.change_account'],
        'su_from_accounts': 'accounts.view_account',
    }

    @action(methods=['get'], detail=False, url_path='su-from-accounts')
    def su_from_accounts(self, request, *args, **kwargs):
        account_id = request.query_params.get('account')
        asset_id = request.query_params.get('asset')

        if account_id:
            account = get_object_or_404(Account, pk=account_id)
            accounts = account.get_su_from_accounts()
        elif asset_id:
            asset = get_object_or_404(Asset, pk=asset_id)
            accounts = asset.accounts.all()
        else:
            accounts = []
        accounts = self.filter_queryset(accounts)
        serializer = serializers.AccountSerializer(accounts, many=True)
        return Response(data=serializer.data)


class AccountSecretsViewSet(RecordViewLogMixin, AccountViewSet):
    """
    因为可能要导出所有账号，所以单独建立了一个 viewset
    """
    serializer_classes = {
        'default': serializers.AccountSecretSerializer,
    }
    http_method_names = ['get', 'options']
    permission_classes = [RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    rbac_perms = {
        'list': 'accounts.view_accountsecret',
        'retrieve': 'accounts.view_accountsecret',
    }


class AccountHistoriesSecretAPI(RecordViewLogMixin, ListAPIView):
    model = Account.history.model
    serializer_class = serializers.AccountHistorySerializer
    http_method_names = ['get', 'options']
    permission_classes = [RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    rbac_perms = {
        'list': 'accounts.view_accountsecret',
    }

    def get_queryset(self):
        return self.model.objects.filter(id=self.kwargs.get('pk'))
