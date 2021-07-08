from django.db.models import F
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response

from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser, NeedMFAVerify
from ..tasks.account_connectivity import test_accounts_connectivity_manual
from ..models import AuthBook
from .. import serializers

__all__ = ['AccountViewSet', 'AccountSecretsViewSet']


class AccountViewSet(OrgBulkModelViewSet):
    model = AuthBook
    filterset_fields = ("username", "asset", "systemuser")
    search_fields = filterset_fields
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
