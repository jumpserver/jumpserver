from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from accounts import serializers
from accounts.filters import AccountFilterSet
from accounts.mixins import AccountRecordViewLogMixin
from accounts.models import Account
from assets.models import Asset, Node
from authentication.permissions import UserConfirmation, ConfirmType
from common.api.mixin import ExtraFilterFieldsMixin
from common.permissions import IsValidUser
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission

__all__ = [
    'AccountViewSet', 'AccountSecretsViewSet',
    'AccountHistoriesSecretAPI', 'AssetAccountBulkCreateApi',
]


class AccountViewSet(OrgBulkModelViewSet):
    model = Account
    search_fields = ('username', 'name', 'asset__name', 'asset__address', 'comment')
    filterset_class = AccountFilterSet
    serializer_classes = {
        'default': serializers.AccountSerializer,
        'retrieve': serializers.AccountDetailSerializer,
    }
    rbac_perms = {
        'partial_update': ['accounts.change_account'],
        'su_from_accounts': 'accounts.view_account',
        'clear_secret': 'accounts.change_account',
    }
    export_as_zip = True

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

    @action(
        methods=['post'], detail=False, url_path='username-suggestions',
        permission_classes=[IsValidUser]
    )
    def username_suggestions(self, request, *args, **kwargs):
        asset_ids = request.data.get('assets', [])
        node_ids = request.data.get('nodes', [])
        username = request.data.get('username', '')

        accounts = Account.objects.all()
        if node_ids:
            nodes = Node.objects.filter(id__in=node_ids)
            node_asset_ids = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
            asset_ids.extend(node_asset_ids)

        if asset_ids:
            accounts = accounts.filter(asset_id__in=list(set(asset_ids)))

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


class AccountSecretsViewSet(AccountRecordViewLogMixin, AccountViewSet):
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


class AssetAccountBulkCreateApi(CreateAPIView):
    serializer_class = serializers.AssetAccountBulkSerializer
    rbac_perms = {
        'POST': 'accounts.add_account',
    }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.create(serializer.validated_data)
        serializer = serializers.AssetAccountBulkSerializerResultSerializer(data, many=True)
        return Response(data=serializer.data, status=HTTP_200_OK)


class AccountHistoriesSecretAPI(ExtraFilterFieldsMixin, AccountRecordViewLogMixin, ListAPIView):
    model = Account.history.model
    serializer_class = serializers.AccountHistorySerializer
    http_method_names = ['get', 'options']
    permission_classes = [RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    rbac_perms = {
        'GET': 'accounts.view_accountsecret',
    }

    def get_object(self):
        return get_object_or_404(Account, pk=self.kwargs.get('pk'))

    @staticmethod
    def filter_spm_queryset(resource_ids, queryset):
        return queryset.filter(history_id__in=resource_ids)

    def get_queryset(self):
        account = self.get_object()
        histories = account.history.all()
        latest_history = account.history.first()
        if not latest_history:
            return histories
        if account.secret != latest_history.secret:
            return histories
        if account.secret_type != latest_history.secret_type:
            return histories
        histories = histories.exclude(history_id=latest_history.history_id)
        return histories
