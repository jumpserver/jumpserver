# -*- coding: utf-8 -*-
#

from accounts.models import PushAccountAutomation
from accounts.serializers import PushAccountAutomationSerializer
from orgs.mixins.api import OrgBulkModelViewSet

__all__ = ['PushAccountAutomationViewSet']


class PushAccountAutomationViewSet(OrgBulkModelViewSet):
    model = PushAccountAutomation
    filter_fields = ('name', 'secret_type', 'secret_strategy')
    search_fields = filter_fields
    ordering_fields = ('name',)
    serializer_class = PushAccountAutomationSerializer
