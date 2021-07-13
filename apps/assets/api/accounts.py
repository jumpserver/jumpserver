from django.db.models import F, Q
from django.conf import settings
from rest_framework.decorators import action
from django_filters import rest_framework as filters
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser, NeedMFAVerify
from common.drf.filters import BaseFilterSet
from ..tasks.account_connectivity import test_accounts_connectivity_manual
from ..models import AuthBook
from .. import serializers

__all__ = ['AccountViewSet', 'AccountSecretsViewSet', 'AccountTaskCreateAPI']


class AccountFilterSet(BaseFilterSet):
    username = filters.CharFilter(method='do_nothing')
    ip = filters.CharFilter(field_name='ip', lookup_expr='exact')
    hostname = filters.CharFilter(field_name='hostname', lookup_expr='exact')

    @property
    def qs(self):
        qs = super().qs
        qs = self.filter_username(qs)
        return qs

    def filter_username(self, qs):
        username = self.get_query_param('username')
        if not username:
            return qs
        qs = qs.filter(Q(username=username) | Q(systemuser__username=username)).distinct()
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
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        queryset = super().get_queryset()\
            .annotate(ip=F('asset__ip'))\
            .annotate(hostname=F('asset__hostname'))
        return queryset

    @action(methods=['post'], detail=True, url_path='verify')
    def verify_account(self, request, *args, **kwargs):
        account = super().get_object()
        task = test_accounts_connectivity_manual.delay([account])
        return Response(data={'task': task.id})


class AccountSecretsViewSet(AccountViewSet):
    """
    因为可能要导出所有账号，所以单独建立了一个 viewset
    """
    serializer_classes = {
        'default': serializers.AccountSecretSerializer
    }
    permission_classes = (IsOrgAdmin, NeedMFAVerify)
    http_method_names = ['get']

    def get_permissions(self):
        if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser]
        return super().get_permissions()


class AccountTaskCreateAPI(CreateAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.AccountTaskSerializer
    filterset_fields = AccountViewSet.filterset_fields
    search_fields = AccountViewSet.search_fields
    filterset_class = AccountViewSet.filterset_class

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
