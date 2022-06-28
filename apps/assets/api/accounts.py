from django.db.models import Q
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from orgs.mixins.api import OrgBulkModelViewSet
from rbac.permissions import RBACPermission
from common.drf.filters import BaseFilterSet
from common.mixins import RecordViewLogMixin
from common.permissions import UserConfirmation
from authentication.const import ConfirmType
from ..tasks.account_connectivity import test_accounts_connectivity_manual
from ..models import AuthBook, Node
from .. import serializers

__all__ = ['AccountFilterSet', 'AccountViewSet', 'AccountSecretsViewSet', 'AccountTaskCreateAPI']


class AccountFilterSet(BaseFilterSet):
    username = filters.CharFilter(method='do_nothing')
    ip = filters.CharFilter(field_name='ip', lookup_expr='exact')
    hostname = filters.CharFilter(field_name='hostname', lookup_expr='exact')
    node = filters.CharFilter(method='do_nothing')

    @property
    def qs(self):
        qs = super().qs
        qs = self.filter_username(qs)
        qs = self.filter_node(qs)
        qs = qs.distinct()
        return qs

    def filter_username(self, qs):
        username = self.get_query_param('username')
        if not username:
            return qs
        qs = qs.filter(Q(username=username) | Q(systemuser__username=username)).distinct()
        return qs

    def filter_node(self, qs):
        node_id = self.get_query_param('node')
        if not node_id:
            return qs
        node = get_object_or_404(Node, pk=node_id)
        node_ids = node.get_all_children(with_self=True).values_list('id', flat=True)
        node_ids = list(node_ids)
        qs = qs.filter(asset__nodes__in=node_ids)
        return qs

    class Meta:
        model = AuthBook
        fields = [
            'asset', 'systemuser', 'id',
        ]


class AccountViewSet(OrgBulkModelViewSet):
    model = AuthBook
    filterset_fields = ("username", "asset", "systemuser", 'ip', 'hostname')
    search_fields = ('username', 'ip', 'hostname', 'systemuser__username')
    filterset_class = AccountFilterSet
    serializer_classes = {
        'default': serializers.AccountSerializer,
        'verify_account': serializers.AssetTaskSerializer
    }
    rbac_perms = {
        'verify_account': 'assets.test_authbook',
        'partial_update': 'assets.change_assetaccountsecret',
    }

    def get_queryset(self):
        queryset = AuthBook.get_queryset()
        return queryset

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
        queryset = AuthBook.objects.all()
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
