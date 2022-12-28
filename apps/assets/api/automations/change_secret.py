# -*- coding: utf-8 -*-
#

from rest_framework import mixins

from assets import serializers
from assets.models import ChangeSecretAutomation, ChangeSecretRecord, AutomationExecution
from common.utils import get_object_or_none
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    'ChangeSecretAutomationViewSet', 'ChangeSecretRecordViewSet',
    'ChangSecretExecutionViewSet'
]


class ChangeSecretAutomationViewSet(OrgBulkModelViewSet):
    model = ChangeSecretAutomation
    filter_fields = ('name', 'secret_type', 'secret_strategy')
    search_fields = filter_fields
    ordering_fields = ('name',)
    serializer_class = serializers.ChangeSecretAutomationSerializer


class ChangeSecretRecordViewSet(mixins.ListModelMixin, OrgGenericViewSet):
    serializer_class = serializers.ChangeSecretRecordSerializer
    filter_fields = ['asset', 'execution_id']
    search_fields = ['asset__hostname']

    def get_queryset(self):
        return ChangeSecretRecord.objects.all()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        eid = self.request.GET.get('execution_id')
        execution = get_object_or_none(AutomationExecution, pk=eid)
        if execution:
            queryset = queryset.filter(execution=execution)
        queryset = queryset.order_by('-date_started')
        return queryset


class ChangSecretExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "assets.view_changesecretexecution"),
        ("retrieve", "assets.view_changesecretexecution"),
        ("create", "assets.add_changesecretexecution"),
    )
