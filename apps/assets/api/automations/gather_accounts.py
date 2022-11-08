# -*- coding: utf-8 -*-
#
from orgs.mixins.api import OrgBulkModelViewSet

from assets.models import GatherAccountsAutomation
from assets import serializers

__all__ = [
    'GatherAccountsAutomationViewSet',
]


class GatherAccountsAutomationViewSet(OrgBulkModelViewSet):
    model = GatherAccountsAutomation
    filter_fields = ('name',)
    search_fields = filter_fields
    ordering_fields = ('name',)
    serializer_class = serializers.GatherAccountAutomationSerializer
