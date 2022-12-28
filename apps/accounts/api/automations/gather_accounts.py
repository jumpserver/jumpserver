# -*- coding: utf-8 -*-
#
from assets import serializers
from assets.models import GatherAccountsAutomation
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    'GatherAccountsAutomationViewSet', 'GatherAccountsExecutionViewSet'
]


class GatherAccountsAutomationViewSet(OrgBulkModelViewSet):
    model = GatherAccountsAutomation
    filter_fields = ('name',)
    search_fields = filter_fields
    ordering_fields = ('name',)
    serializer_class = serializers.GatherAccountAutomationSerializer


class GatherAccountsExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "assets.view_gatheraccountsexecution"),
        ("retrieve", "assets.view_gatheraccountsexecution"),
        ("create", "assets.add_gatheraccountsexecution"),
    )
