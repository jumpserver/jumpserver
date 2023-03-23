from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from accounts import serializers
from accounts.filters import AccountFilterSet
from accounts.models import Account
from assets.models import Asset, Node
from common.permissions import UserConfirmation, ConfirmType
from common.views.mixins import RecordViewLogMixin
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission

__all__ = [
    'AccountViewSet', 'AccountSecretsViewSet',
    'AccountHistoriesSecretAPI'
]


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
        'username_suggestions': 'accounts.view_account',
        'clear_secret': 'accounts.change_account',
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
            accounts = Account.objects.none()
        accounts = self.filter_queryset(accounts)
        serializer = serializers.AccountSerializer(accounts, many=True)
        return Response(data=serializer.data)

    @action(methods=['get'], detail=False, url_path='username-suggestions')
    def username_suggestions(self, request, *args, **kwargs):
        asset_ids = request.query_params.get('assets')
        node_keys = request.query_params.get('keys')
        username = request.query_params.get('username')

        assets = Asset.objects.all()
        if asset_ids:
            assets = assets.filter(id__in=asset_ids.split(','))
        if node_keys:
            patten = Node.get_node_all_children_key_pattern(node_keys.split(','))
            assets = assets.filter(nodes__key__regex=patten)

        accounts = Account.objects.filter(asset__in=assets)
        if username:
            accounts = accounts.filter(username__icontains=username)
        usernames = list(accounts.values_list('username', flat=True).distinct()[:10])
        usernames.sort()
        common = [i for i in usernames if i in usernames if i.lower() in ['root', 'admin', 'administrator']]
        others = [i for i in usernames if i not in common]
        usernames = common + others
        return Response(data=usernames)

    @action(methods=['patch'], detail=False, url_path='clear-secret')
    def clear_secret(self, request, *args, **kwargs):
        account_ids = request.data.get('account_ids', [])
        self.model.objects.filter(id__in=account_ids).update(secret=None)
        return Response(status=HTTP_200_OK)

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
        'GET': 'accounts.view_accountsecret',
    }

    def get_object(self):
        return get_object_or_404(Account, pk=self.kwargs.get('pk'))

    def get_queryset(self):
        account = self.get_object()
        histories = account.history.all()
        last_history = account.history.first()
        if not last_history:
            return histories

        if account.secret == last_history.secret \
                and account.secret_type == last_history.secret_type:
            histories = histories.exclude(history_id=last_history.history_id)
        return histories
