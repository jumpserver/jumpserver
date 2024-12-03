# -*- coding: utf-8 -*-
#
from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import (
    BackupAccountAutomation
)
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    'AccountBackupPlanViewSet', 'BackupAccountExecutionViewSet'
]


class AccountBackupPlanViewSet(OrgBulkModelViewSet):
    model = BackupAccountAutomation
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.BackupAccountSerializer


class BackupAccountExecutionViewSet(AutomationExecutionViewSet):
    serializer_class = serializers.BackupAccountExecutionSerializer
    http_method_names = ['get', 'post', 'options']
    tp = AutomationTypes.backup_account

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(automation__type=self.tp)
        return queryset
