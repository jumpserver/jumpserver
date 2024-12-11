# -*- coding: utf-8 -*-
#
from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import PushAccountAutomation
from orgs.mixins.api import OrgBulkModelViewSet

from .base import (
    AutomationAssetsListApi, AutomationRemoveAssetApi, AutomationAddAssetApi,
    AutomationNodeAddRemoveApi, AutomationExecutionViewSet
)

__all__ = [
    'PushAccountAutomationViewSet', 'PushAccountAssetsListApi', 'PushAccountRemoveAssetApi',
    'PushAccountAddAssetApi', 'PushAccountNodeAddRemoveApi', 'PushAccountExecutionViewSet',
]


class PushAccountAutomationViewSet(OrgBulkModelViewSet):
    model = PushAccountAutomation
    filterset_fields = ('name', 'secret_type', 'secret_strategy')
    search_fields = filterset_fields
    serializer_class = serializers.PushAccountAutomationSerializer


class PushAccountExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_pushaccountexecution"),
        ("retrieve", "accounts.view_pushaccountexecution"),
        ("create", "accounts.add_pushaccountexecution"),
        ("report", "accounts.view_pushaccountexecution"),
    )

    tp = AutomationTypes.push_account

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(automation__type=self.tp)
        return queryset


class PushAccountAssetsListApi(AutomationAssetsListApi):
    model = PushAccountAutomation


class PushAccountRemoveAssetApi(AutomationRemoveAssetApi):
    model = PushAccountAutomation
    serializer_class = serializers.PushAccountUpdateAssetSerializer


class PushAccountAddAssetApi(AutomationAddAssetApi):
    model = PushAccountAutomation
    serializer_class = serializers.PushAccountUpdateAssetSerializer


class PushAccountNodeAddRemoveApi(AutomationNodeAddRemoveApi):
    model = PushAccountAutomation
    serializer_class = serializers.PushAccountUpdateNodeSerializer
