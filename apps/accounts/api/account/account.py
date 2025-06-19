from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from accounts import serializers
from accounts.const import ChangeSecretRecordStatusChoice
from accounts.filters import AccountFilterSet, NodeFilterBackend
from accounts.mixins import AccountRecordViewLogMixin
from accounts.models import Account, ChangeSecretRecord
from assets.models import Asset, Node
from authentication.permissions import UserConfirmation, ConfirmType
from common.api.mixin import ExtraFilterFieldsMixin
from common.drf.filters import AttrRulesFilterBackend
from common.permissions import IsValidUser
from common.utils import lazyproperty, get_logger
from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission

logger = get_logger(__file__)

__all__ = [
    'AccountViewSet', 'AccountSecretsViewSet',
    'AccountHistoriesSecretAPI', 'AssetAccountBulkCreateApi',
]


class AccountViewSet(OrgBulkModelViewSet):
    model = Account
    search_fields = ('username', 'name', 'asset__name', 'asset__address', 'comment')
    extra_filter_backends = [AttrRulesFilterBackend, NodeFilterBackend]
    filterset_class = AccountFilterSet
    serializer_classes = {
        'default': serializers.AccountSerializer,
        'retrieve': serializers.AccountDetailSerializer,
    }
    rbac_perms = {
        'partial_update': ['accounts.change_account'],
        'su_from_accounts': 'accounts.view_account',
        'clear_secret': 'accounts.change_account',
        'move_to_assets': 'accounts.create_account',
        'copy_to_assets': 'accounts.create_account',
    }
    export_as_zip = True

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.query_params.get('asset') or self.request.query_params.get('asset_id')
        if not asset_id:
            return queryset

        asset = get_object_or_404(Asset, pk=asset_id)
        queryset = asset.all_accounts.all()
        return queryset

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
        raw_asset_ids = request.data.get('assets', [])
        node_ids = request.data.get('nodes', [])
        username = request.data.get('username', '')

        asset_ids = set(raw_asset_ids)

        if node_ids:
            nodes = Node.objects.filter(id__in=node_ids)
            node_asset_qs = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
            asset_ids |= {str(u) for u in node_asset_qs}

        if asset_ids:
            through = Asset.directory_services.through
            ds_qs = through.objects.filter(asset_id__in=asset_ids) \
                .values_list('directoryservice_id', flat=True)
            asset_ids |= {str(u) for u in ds_qs}
            accounts = Account.objects.filter(asset_id__in=list(asset_ids))
        else:
            accounts = Account.objects.all()

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

    def _copy_or_move_to_assets(self, request, move=False):
        account = self.get_object()
        asset_ids = request.data.get('assets', [])
        assets = Asset.objects.filter(id__in=asset_ids)
        field_names = [
            'name', 'username', 'secret_type', 'secret',
            'privileged', 'is_active', 'source', 'source_id', 'comment'
        ]
        account_data = {field: getattr(account, field) for field in field_names}

        creation_results = {}
        success_count = 0

        for asset in assets:
            account_data['asset'] = asset
            creation_results[asset] = {'state': 'created'}
            try:
                with transaction.atomic():
                    self.model.objects.create(**account_data)
                    success_count += 1
            except Exception as e:
                logger.debug(f'{"Move" if move else "Copy"} to assets error: {e}')
                creation_results[asset] = {'error': _('Account already exists'), 'state': 'error'}

        results = [{'asset': str(asset), **res} for asset, res in creation_results.items()]

        if move and success_count > 0:
            account.delete()

        return Response(results, status=HTTP_200_OK)

    @action(methods=['post'], detail=True, url_path='move-to-assets')
    def move_to_assets(self, request, *args, **kwargs):
        return self._copy_or_move_to_assets(request, move=True)

    @action(methods=['post'], detail=True, url_path='copy-to-assets')
    def copy_to_assets(self, request, *args, **kwargs):
        return self._copy_or_move_to_assets(request, move=False)


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

    @lazyproperty
    def account(self) -> Account:
        return get_object_or_404(Account, pk=self.kwargs.get('pk'))

    def get_object(self):
        return self.account

    @lazyproperty
    def latest_history(self):
        return self.account.history.first()

    @property
    def latest_change_secret_record(self) -> ChangeSecretRecord:
        return self.account.changesecretrecords.filter(
            status=ChangeSecretRecordStatusChoice.pending
        ).order_by('-date_created').first()

    @staticmethod
    def filter_spm_queryset(resource_ids, queryset):
        return queryset.filter(history_id__in=resource_ids)

    def get_queryset(self):
        account = self.account
        histories = account.history.all()
        latest_history = self.latest_history
        if not latest_history:
            return histories
        if account.secret != latest_history.secret:
            return histories
        if account.secret_type != latest_history.secret_type:
            return histories
        histories = histories.exclude(history_id=latest_history.history_id)
        return histories

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = list(queryset)
        latest_history = self.latest_history
        if not latest_history:
            return queryset

        latest_change_secret_record = self.latest_change_secret_record
        if not latest_change_secret_record:
            return queryset

        if latest_change_secret_record.date_created > latest_history.history_date:
            temp_history = self.model(
                secret=latest_change_secret_record.new_secret,
                secret_type=self.account.secret_type,
                version=latest_history.version,
                history_date=latest_change_secret_record.date_created,
            )
            queryset = [temp_history] + queryset

        return queryset
