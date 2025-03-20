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
    'BackupAccountViewSet', 'BackupAccountExecutionViewSet'
]


class BackupAccountViewSet(OrgBulkModelViewSet):
    model = BackupAccountAutomation
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.BackupAccountSerializer


class BackupAccountExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_backupaccountexecution"),
        ("retrieve", "accounts.view_backupaccountexecution"),
        ("create", "accounts.add_backupaccountexecution"),
        ("report", "accounts.view_backupaccountexecution"),
    )

    tp = AutomationTypes.backup_account

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(type=self.tp)
        return queryset
