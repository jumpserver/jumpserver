# -*- coding: utf-8 -*-
#
from django.db.models import Q, Count
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from operator import itemgetter

from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import CheckAccountAutomation, AccountRisk, RiskChoice, CheckAccountEngine
from common.api import JMSModelViewSet
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    'CheckAccountAutomationViewSet', 'CheckAccountExecutionViewSet',
    'AccountRiskViewSet', 'CheckAccountEngineViewSet',
]

from ...risk_handlers import RiskHandler


class CheckAccountAutomationViewSet(OrgBulkModelViewSet):
    model = CheckAccountAutomation
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.CheckAccountAutomationSerializer


class CheckAccountExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_checkaccountexecution"),
        ("retrieve", "accounts.view_checkaccountsexecution"),
        ("create", "accounts.add_checkaccountexecution"),
        ("report", "accounts.view_checkaccountsexecution"),
    )
    ordering = ('-date_created',)
    tp = AutomationTypes.check_account

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(automation__type=self.tp)
        return queryset


class AccountRiskViewSet(OrgBulkModelViewSet):
    model = AccountRisk
    search_fields = ('username', 'asset')
    filterset_fields = ('risk', 'status', 'asset')
    serializer_classes = {
        'default': serializers.AccountRiskSerializer,
        'assets': serializers.AssetRiskSerializer,
        'handle': serializers.HandleRiskSerializer
    }
    ordering_fields = (
        'asset', 'risk', 'status',  'username', 'date_created'
    )
    ordering = ('-asset', 'date_created')
    rbac_perms = {
        'sync_accounts': 'assets.add_accountrisk',
        'assets': 'accounts.view_accountrisk',
        'handle': 'accounts.change_accountrisk'
    }

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed('PUT')

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed('POST')

    @action(methods=['get'], detail=False, url_path='assets')
    def assets(self, request, *args, **kwargs):
        annotations = {
            f'{risk[0]}_count': Count('id', filter=Q(risk=risk[0]))
            for risk in RiskChoice.choices
        }
        queryset = (
            AccountRisk.objects
            .select_related('asset', 'asset__platform')  # 使用 select_related 来优化 asset 和 asset__platform 的查询
            .values('asset__id', 'asset__name', 'asset__address', 'asset__platform__name')  # 添加需要的字段
            .annotate(risk_total=Count('id'))  # 计算风险总数
            .annotate(**annotations)  # 使用上面定义的 annotations 进行计数
        )
        return self.get_paginated_response_from_queryset(queryset)

    @action(methods=['post'], detail=False, url_path='handle')
    def handle(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        asset, username, act, risk = itemgetter('asset', 'username', 'action', 'risk')(serializer.validated_data)
        handler = RiskHandler(asset=asset, username=username)
        data = handler.handle(act, risk)
        if not data:
            data = {'message': 'Success'}
        return Response(data)

        # 处理风险

    def handle_add_account(self):
        pass

    def handle_disable_remote(self):
        pass

    def handle_delete_remote(self):
        pass

    def handle_delete_both(self):
        pass


class CheckAccountEngineViewSet(JMSModelViewSet):
    search_fields = ('name',)
    serializer_class = serializers.CheckAccountEngineSerializer

    def get_queryset(self):
        return CheckAccountEngine.objects.all()

