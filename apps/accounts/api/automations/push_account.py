# -*- coding: utf-8 -*-
#

from assets.models import PushAccountAutomation
from assets.serializers import PushAccountAutomationSerializer
from orgs.mixins.api import OrgBulkModelViewSet

__all__ = ['PushAccountAutomationViewSet']


class PushAccountAutomationViewSet(OrgBulkModelViewSet):
    model = PushAccountAutomation
    filter_fields = ('name', 'secret_type', 'secret_strategy')
    search_fields = filter_fields
    ordering_fields = ('name',)
    serializer_class = PushAccountAutomationSerializer
