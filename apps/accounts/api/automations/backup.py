# -*- coding: utf-8 -*-
#
from rest_framework import status, viewsets
from rest_framework.response import Response

from accounts import serializers
from accounts.models import (
    AccountBackupAutomation, AccountBackupExecution
)
from accounts.tasks import execute_account_backup_task
from common.const.choices import Trigger
from orgs.mixins.api import OrgBulkModelViewSet

__all__ = [
    'AccountBackupPlanViewSet', 'AccountBackupPlanExecutionViewSet'
]


class AccountBackupPlanViewSet(OrgBulkModelViewSet):
    model = AccountBackupAutomation
    filterset_fields = ('name',)
    search_fields = filterset_fields
    ordering = ('name',)
    serializer_class = serializers.AccountBackupSerializer


class AccountBackupPlanExecutionViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AccountBackupPlanExecutionSerializer
    search_fields = ('trigger', 'plan__name')
    filterset_fields = ('trigger', 'plan_id', 'plan__name')
    http_method_names = ['get', 'post', 'options']

    def get_queryset(self):
        queryset = AccountBackupExecution.objects.all()
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pid = serializer.data.get('plan')
        task = execute_account_backup_task.delay(pid=str(pid), trigger=Trigger.manual)
        return Response({'task': task.id}, status=status.HTTP_201_CREATED)
