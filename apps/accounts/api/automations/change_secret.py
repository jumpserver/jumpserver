# -*- coding: utf-8 -*-
#
from django.db import transaction
from django.db.models import Max, Q, Subquery, OuterRef
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import (
    AutomationTypes, ChangeSecretRecordStatusChoice
)
from accounts.filters import (
    ChangeSecretAutomationFilterSet, ChangeSecretRecordFilterSet,
    ChangeSecretStatusFilterSet,
)
from accounts.models import ChangeSecretAutomation, ChangeSecretRecord, Account
from accounts.tasks import (
    execute_automation_record_task, verify_change_secret_records_task,
)
from accounts.utils import account_secret_task_status
from authentication.permissions import UserConfirmation, ConfirmType
from common.permissions import IsValidLicense
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
    'ChangSecretNodeAddRemoveApi', 'ChangeSecretStatusViewSet'
]


class ChangeSecretAutomationViewSet(OrgBulkModelViewSet):
    model = ChangeSecretAutomation
    permission_classes = [RBACPermission, IsValidLicense]
    filterset_class = ChangeSecretAutomationFilterSet
    search_fields = ('name',)
    serializer_classes = {
        'default': serializers.ChangeSecretAutomationSerializer,
        'list': serializers.ChangeSecretAutomationListSerializer,
    }


class ChangeSecretRecordViewSet(mixins.ListModelMixin, OrgGenericViewSet):
    filterset_class = ChangeSecretRecordFilterSet
    permission_classes = [RBACPermission, IsValidLicense]
    search_fields = ('asset__address', 'account__username')
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
        'verify': [
            'accounts.view_changesecretrecord',
            'accounts.verify_account',
        ],
        'restore': [
            'accounts.view_changesecretrecord',
            'accounts.change_account',
        ],
    }

    def get_permissions(self):
        if self.action == 'secret':
            self.permission_classes = [
                RBACPermission,
                UserConfirmation.require(ConfirmType.MFA)
            ]
        elif self.action == 'restore':
            self.permission_classes = [
                RBACPermission,
                IsValidLicense,
                UserConfirmation.require(ConfirmType.MFA),
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
        ).filter(Q(status=ChangeSecretRecordStatusChoice.success))

        failed_records = queryset.filter(
            ~Q(account__in=Subquery(recent_success_accounts.values('account'))),
            status__in=[
                ChangeSecretRecordStatusChoice.failed,
                ChangeSecretRecordStatusChoice.unverified,
            ],
            ignore_fail=False
        )
        return failed_records

    def get_queryset(self):
        return ChangeSecretRecord.get_valid_records()

    @action(methods=['post'], detail=False, url_path='execute')
    def execute(self, request, *args, **kwargs):
        record_ids = request.data.get('record_ids')
        records = self.get_queryset().filter(id__in=record_ids)
        if not records.exists():
            return Response(
                {'detail': 'No valid records found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        record_ids = [str(_id) for _id in records.values_list('id', flat=True)]
        task = execute_automation_record_task.delay(record_ids, self.tp)
        return Response({'task': task.id}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='verify')
    def verify(self, request, *args, **kwargs):
        record_ids = request.data.get('record_ids')
        if not isinstance(record_ids, list) or not record_ids:
            return Response(
                {'detail': _('Record IDs must be a non-empty list')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        records = self.get_queryset().filter(
            id__in=record_ids,
            new_secret__isnull=False,
        )
        record_ids = [
            str(record_id)
            for record_id in records.values_list('id', flat=True)
        ]
        if not record_ids:
            return Response(
                {'detail': _('No valid records found')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task = verify_change_secret_records_task.delay(record_ids)
        return Response({'task': task.id}, status=status.HTTP_200_OK)

    @action(methods=['post'], detail=False, url_path='restore')
    def restore(self, request, *args, **kwargs):
        record_ids = request.data.get('record_ids')
        force = request.data.get('force', False)
        if not isinstance(record_ids, list) or not record_ids:
            return Response(
                {'detail': _('Record IDs must be a non-empty list')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(force, bool):
            return Response(
                {'detail': _('Force must be a boolean')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_record_ids = list(
            self.get_queryset().filter(id__in=record_ids)
            .values_list('id', flat=True)
        )
        if not valid_record_ids:
            return Response(
                {'detail': _('No valid records found')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = {
            'restored': 0,
            'already_synced': 0,
            'not_verified': 0,
            'conflicts': [],
        }
        for record_id in valid_record_ids:
            with transaction.atomic():
                record = (
                    self.get_queryset().select_for_update()
                    .select_related('account')
                    .filter(id=record_id)
                    .first()
                )
                if not record or not record.account_id:
                    continue
                verification_status = record.verification_status
                if verification_status == ChangeSecretRecordStatusChoice.pending.value:
                    result['not_verified'] += 1
                    continue
                if (
                        not force
                        and verification_status
                        != ChangeSecretRecordStatusChoice.success.value
                ):
                    result['not_verified'] += 1
                    continue

                account = Account.objects.select_for_update().filter(
                    id=record.account_id
                ).first()
                if not account:
                    continue

                if account.secret == record.new_secret:
                    result['already_synced'] += 1
                elif (
                        (
                            record.account_version is not None
                            and account.version != record.account_version
                        )
                        or account.secret != record.old_secret
                ):
                    result['conflicts'].append({
                        'record': str(record.id),
                        'account': str(account.id),
                    })
                    continue
                else:
                    account.secret = record.new_secret
                    account.date_updated = timezone.now()
                    account.date_change_secret = timezone.now()
                    account.change_secret_status = (
                        ChangeSecretRecordStatusChoice.success.value
                    )
                    account.save(update_fields=[
                        'secret', 'date_updated', 'date_change_secret',
                        'change_secret_status',
                    ])
                    result['restored'] += 1

                record.status = ChangeSecretRecordStatusChoice.success.value
                record.error = ''
                record.ignore_fail = False
                record.save(update_fields=[
                    'status', 'error', 'ignore_fail',
                ])

        return Response(result, status=status.HTTP_200_OK)

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
        ("report", "accounts.view_changesecretexecution"),
    )
    permission_classes = [RBACPermission, IsValidLicense]
    tp = AutomationTypes.change_secret

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(type=self.tp)
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

class ChangeSecretStatusViewSet(OrgBulkModelViewSet):
    perm_model = ChangeSecretAutomation
    filterset_class = ChangeSecretStatusFilterSet
    serializer_class = serializers.ChangeSecretAccountSerializer
    search_fields = ('username',)

    permission_classes = [RBACPermission, IsValidLicense]
    http_method_names = ["get", "delete", "options"]

    def get_queryset(self):
        account_ids = list(account_secret_task_status.account_ids)
        return Account.objects.filter(id__in=account_ids).select_related('asset')

    def bulk_destroy(self, request, *args, **kwargs):
        account_ids = request.data.get('account_ids')
        if isinstance(account_ids, str):
            account_ids = [account_ids]
        for _id in account_ids:
            account_secret_task_status.clear(_id)
        return Response(status=status.HTTP_200_OK)
