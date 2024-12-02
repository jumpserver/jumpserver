# -*- coding: utf-8 -*-
#
from django.db.models import Max, Q, Subquery, OuterRef
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes, ChangeSecretRecordStatusChoice
from accounts.filters import ChangeSecretRecordFilterSet
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
    filterset_class = ChangeSecretRecordFilterSet
    search_fields = ('asset__address', 'account_username')
    ordering_fields = ('date_finished',)
    tp = AutomationTypes.change_secret
    serializer_classes = {
        'default': serializers.ChangeSecretRecordSerializer,
        'secret': serializers.ChangeSecretRecordViewSecretSerializer,
    }
    rbac_perms = {
        'execute': 'accounts.add_changesecretexecution',
        'secret': 'accounts.view_changesecretrecord',
        'dashboard': 'accounts.view_changesecretrecord',
        'ignore_fail': 'accounts.view_changesecretrecord',
    }

    def get_permissions(self):
        if self.action == 'secret':
            self.permission_classes = [
                RBACPermission,
                UserConfirmation.require(ConfirmType.MFA)
            ]
        return super().get_permissions()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        if self.action == 'dashboard':
            return self.get_dashboard_queryset(queryset)
        return queryset

    @staticmethod
    def get_dashboard_queryset(queryset):
        recent_dates = queryset.values('account').annotate(
            max_date_finished=Max('date_finished')
        )

        recent_success_accounts = queryset.filter(
            account=OuterRef('account'),
            date_finished=Subquery(
                recent_dates.filter(account=OuterRef('account')).values('max_date_finished')[:1]
            )
        ).filter(Q(status=ChangeSecretRecordStatusChoice.success) | Q(ignore_fail=True))

        failed_records = queryset.filter(
            ~Q(account__in=Subquery(recent_success_accounts.values('account'))),
            status=ChangeSecretRecordStatusChoice.failed
        )
        return failed_records

    def get_queryset(self):
        qs = ChangeSecretRecord.get_valid_records()
        return qs.filter(
            execution__automation__type=self.tp
        )

    @action(methods=['post'], detail=False, url_path='execute')
    def execute(self, request, *args, **kwargs):
        record_ids = request.data.get('record_ids')
        records = self.get_queryset().filter(id__in=record_ids)
        execution_count = records.values_list('execution_id', flat=True).distinct().count()
        if execution_count != 1:
            return Response(
                {'detail': 'Only one execution is allowed to execute'},
                status=status.HTTP_400_BAD_REQUEST
            )
        task = execute_automation_record_task.delay(record_ids, self.tp)
        return Response({'task': task.id}, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=True, url_path='secret')
    def secret(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(methods=['get'], detail=False, url_path='dashboard')
    def dashboard(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(methods=['patch'], detail=True, url_path='ignore-fail')
    def ignore_fail(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.ignore_fail = True
        instance.save(update_fields=['ignore_fail'])
        return Response(status=status.HTTP_200_OK)


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
