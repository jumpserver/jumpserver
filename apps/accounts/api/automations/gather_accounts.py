# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.const import Source
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
    filter_fields = ('name',)
    search_fields = filter_fields
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
        'sync_account': 'assets.add_gatheredaccount',
    }

    @action(methods=['post'], detail=True, url_path='sync')
    def sync_account(self, request, *args, **kwargs):
        gathered_account = super().get_object()
        asset = gathered_account.asset
        username = gathered_account.username
        accounts = asset.accounts.filter(username=username)

        if accounts.exists():
            accounts.update(source=Source.COLLECTED)
        else:
            asset.accounts.model.objects.create(
                asset=asset, username=username,
                name=f'{username}-{_("Collected")}',
                source=Source.COLLECTED
            )
        return Response(status=status.HTTP_201_CREATED)
