# -*- coding: utf-8 -*-
#
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import AccountCheckAutomation
from accounts.models import AccountRisk
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    'CheckAccountsAutomationViewSet', 'CheckAccountExecutionViewSet',
    'AccountRiskViewSet'
]


class CheckAccountsAutomationViewSet(OrgBulkModelViewSet):
    model = AccountCheckAutomation
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.CheckAccountsAutomationSerializer


class CheckAccountExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_gatheraccountsexecution"),
        ("retrieve", "accounts.view_gatheraccountsexecution"),
        ("create", "accounts.add_gatheraccountsexecution"),
    )

    tp = AutomationTypes.gather_accounts

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(automation__type=self.tp)
        return queryset


class AccountRiskViewSet(OrgBulkModelViewSet):
    model = AccountRisk
    search_fields = ('username',)
    filterset_class = AccountRiskFilterSet
    serializer_classes = {
        'default': serializers.AccountRiskSerializer,
    }
    rbac_perms = {
        'sync_accounts': 'assets.add_AccountRisk',
    }

    @action(methods=['post'], detail=False, url_path='sync-accounts')
    def sync_accounts(self, request, *args, **kwargs):
        gathered_account_ids = request.data.get('gathered_account_ids')
        gathered_accounts = self.model.objects.filter(id__in=gathered_account_ids)
        self.model.sync_accounts(gathered_accounts)
        return Response(status=status.HTTP_201_CREATED)
