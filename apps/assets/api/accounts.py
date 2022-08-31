from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission
from common.drf.filters import BaseFilterSet, UUIDInFilter
from common.mixins import RecordViewLogMixin
from common.permissions import UserConfirmation
from authentication.const import ConfirmType
from ..tasks.account_connectivity import test_accounts_connectivity_manual
from ..models import Account, Node
from .. import serializers

__all__ = ['AccountFilterSet', 'AccountViewSet', 'AccountSecretsViewSet', 'AccountTaskCreateAPI']


class AccountFilterSet(BaseFilterSet):
    ip = filters.CharFilter(field_name='ip', lookup_expr='exact')
    hostname = filters.CharFilter(field_name='name', lookup_expr='exact')
    username = filters.CharFilter(field_name="username", lookup_expr='exact')
    assets = UUIDInFilter(field_name='asset_id', lookup_expr='in')
    nodes = UUIDInFilter(method='filter_nodes')

    def filter_nodes(self, queryset, name, value):
        nodes = Node.objects.filter(id__in=value)
        if not nodes:
            return queryset

        node_qs = Node.objects.none()
        for node in nodes:
            node_qs |= node.get_all_children(with_self=True)
        node_ids = list(node_qs.values_list('id', flat=True))
        queryset = queryset.filter(asset__nodes__in=node_ids)
        return queryset

    class Meta:
        model = Account
        fields = [
            'asset', 'id'
        ]


class AccountViewSet(OrgBulkModelViewSet):
    model = Account
    filterset_fields = ("username", "asset", 'ip', 'name')
    search_fields = ('username', 'ip', 'name')
    filterset_class = AccountFilterSet
    serializer_classes = {
        'default': serializers.AccountSerializer,
        'verify_account': serializers.AssetTaskSerializer
    }
    rbac_perms = {
        'verify_account': 'assets.test_authbook',
        'partial_update': 'assets.change_assetaccountsecret',
    }

    @action(methods=['post'], detail=True, url_path='verify')
    def verify_account(self, request, *args, **kwargs):
        account = super().get_object()
        task = test_accounts_connectivity_manual.delay([account])
        return Response(data={'task': task.id})


class AccountSecretsViewSet(RecordViewLogMixin, AccountViewSet):
    """
    因为可能要导出所有账号，所以单独建立了一个 viewset
    """
    serializer_classes = {
        'default': serializers.AccountSecretSerializer
    }
    http_method_names = ['get']
    permission_classes = [RBACPermission, UserConfirmation.require(ConfirmType.MFA)]
    rbac_perms = {
        'list': 'assets.view_assetaccountsecret',
        'retrieve': 'assets.view_assetaccountsecret',
    }


class AccountTaskCreateAPI(CreateAPIView):
    serializer_class = serializers.AccountTaskSerializer
    filterset_fields = AccountViewSet.filterset_fields
    search_fields = AccountViewSet.search_fields
    filterset_class = AccountViewSet.filterset_class

    def check_permissions(self, request):
        return request.user.has_perm('assets.test_assetconnectivity')

    def get_accounts(self):
        queryset = Account.objects.all()
        queryset = self.filter_queryset(queryset)
        return queryset

    def perform_create(self, serializer):
        accounts = self.get_accounts()
        task = test_accounts_connectivity_manual.delay(accounts)
        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)
        return task

    def get_exception_handler(self):
        def handler(e, context):
            return Response({"error": str(e)}, status=400)
        return handler
