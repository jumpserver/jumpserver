# -*- coding: utf-8 -*-
#
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.filters import GatheredAccountFilterSet
from accounts.models import GatherAccountsAutomation
from accounts.models import GatheredAccount
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    'GatherAccountsAutomationViewSet', 'GatherAccountsExecutionViewSet',
    'GatheredAccountViewSet'
]


class GatherAccountsAutomationViewSet(OrgBulkModelViewSet):
    model = GatherAccountsAutomation
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.GatherAccountAutomationSerializer


class GatherAccountsExecutionViewSet(AutomationExecutionViewSet):
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


class GatheredAccountViewSet(OrgBulkModelViewSet):
    model = GatheredAccount
    search_fields = ('username',)
    filterset_class = GatheredAccountFilterSet
    serializer_classes = {
        'default': serializers.GatheredAccountSerializer,
    }
    rbac_perms = {
        'sync_accounts': 'assets.add_gatheredaccount',
    }

    @action(methods=['post'], detail=False, url_path='sync-accounts')
    def sync_accounts(self, request, *args, **kwargs):
        gathered_account_ids = request.data.get('gathered_account_ids')
        gathered_accounts = self.model.objects.filter(id__in=gathered_account_ids)
        self.model.sync_accounts(gathered_accounts)
        return Response(status=status.HTTP_201_CREATED)
