# -*- coding: utf-8 -*-
#
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import ChangeSecretAutomation, ChangeSecretRecord
from accounts.tasks import execute_automation_record_task
from authentication.permissions import UserConfirmation, ConfirmType
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from rbac.permissions import RBACPermission
from .base import (
    AutomationAssetsListApi, AutomationRemoveAssetApi, AutomationAddAssetApi,
    AutomationNodeAddRemoveApi, AutomationExecutionViewSet
)

__all__ = [
    'ChangeSecretAutomationViewSet', 'ChangeSecretRecordViewSet',
    'ChangSecretExecutionViewSet', 'ChangSecretAssetsListApi',
    'ChangSecretRemoveAssetApi', 'ChangSecretAddAssetApi',
    'ChangSecretNodeAddRemoveApi'
]


class ChangeSecretAutomationViewSet(OrgBulkModelViewSet):
    model = ChangeSecretAutomation
    filterset_fields = ('name', 'secret_type', 'secret_strategy')
    search_fields = filterset_fields
    serializer_class = serializers.ChangeSecretAutomationSerializer


class ChangeSecretRecordViewSet(mixins.ListModelMixin, OrgGenericViewSet):
    filterset_fields = ('asset_id', 'execution_id')
    search_fields = ('asset__address',)
    tp = AutomationTypes.change_secret
    serializer_classes = {
        'default': serializers.ChangeSecretRecordSerializer,
        'secret': serializers.ChangeSecretRecordViewSecretSerializer,
    }
    rbac_perms = {
        'execute': 'accounts.add_changesecretexecution',
        'secret': 'accounts.view_changesecretrecord',
    }

    def get_permissions(self):
        if self.action == 'secret':
            self.permission_classes = [
                RBACPermission,
                UserConfirmation.require(ConfirmType.MFA)
            ]
        return super().get_permissions()

    def get_queryset(self):
        return ChangeSecretRecord.objects.all()

    @action(methods=['post'], detail=False, url_path='execute')
    def execute(self, request, *args, **kwargs):
        record_id = request.data.get('record_id')
        record = self.get_queryset().filter(pk=record_id)
        if not record:
            return Response(
                {'detail': 'record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        task = execute_automation_record_task.delay(record_id, self.tp)
        return Response({'task': task.id}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True, url_path='secret')
    def secret(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ChangSecretExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_changesecretexecution"),
        ("retrieve", "accounts.view_changesecretexecution"),
        ("create", "accounts.add_changesecretexecution"),
    )

    tp = AutomationTypes.change_secret

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(automation__type=self.tp)
        return queryset


class ChangSecretAssetsListApi(AutomationAssetsListApi):
    model = ChangeSecretAutomation


class ChangSecretRemoveAssetApi(AutomationRemoveAssetApi):
    model = ChangeSecretAutomation
    serializer_class = serializers.ChangeSecretUpdateAssetSerializer


class ChangSecretAddAssetApi(AutomationAddAssetApi):
    model = ChangeSecretAutomation
    serializer_class = serializers.ChangeSecretUpdateAssetSerializer


class ChangSecretNodeAddRemoveApi(AutomationNodeAddRemoveApi):
    model = ChangeSecretAutomation
    serializer_class = serializers.ChangeSecretUpdateNodeSerializer
