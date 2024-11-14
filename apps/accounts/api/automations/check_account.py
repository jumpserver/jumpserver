# -*- coding: utf-8 -*-
#
from django.db.models import Q, Count
from rest_framework.decorators import action

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
    )

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
    }
    ordering_fields = (
        'asset', 'risk', 'status',  'username', 'date_created'
    )
    ordering = ('-asset', 'date_created')
    rbac_perms = {
        'sync_accounts': 'assets.add_accountrisk',
        'assets': 'accounts.view_accountrisk'
    }
    http_method_names = ['get', 'head', 'options']

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


class CheckAccountEngineViewSet(JMSModelViewSet):
    search_fields = ('name',)
    serializer_class = serializers.CheckAccountEngineSerializer

    def get_queryset(self):
        return CheckAccountEngine.objects.all()

