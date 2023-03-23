# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import Source, AutomationTypes
from accounts.filters import GatheredAccountFilterSet
from accounts.models import GatherAccountsAutomation, Account
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
        'sync_accounts': 'assets.add_gatheredaccount',
    }

    @action(methods=['post'], detail=False, url_path='sync-accounts')
    def sync_accounts(self, request, *args, **kwargs):
        gathered_account_ids = request.data.get('gathered_account_ids')
        gathered_accounts = self.model.objects.filter(id__in=gathered_account_ids)
        account_objs = []
        exists_accounts = Account.objects.none()
        for gathered_account in gathered_accounts:
            asset_id = gathered_account.asset_id
            username = gathered_account.username
            accounts = Account.objects.filter(asset_id=asset_id, username=username)
            if accounts.exists():
                exists_accounts |= accounts
            else:
                account_objs.append(
                    Account(
                        asset_id=asset_id, username=username,
                        name=f'{username}-{_("Collected")}',
                        source=Source.COLLECTED
                    ))
        exists_accounts.update(source=Source.COLLECTED)
        Account.objects.bulk_create(account_objs)
        return Response(status=status.HTTP_201_CREATED)
