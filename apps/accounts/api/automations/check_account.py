# -*- coding: utf-8 -*-
#
from django.db.models import Q, Count
from rest_framework.decorators import action

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import AccountCheckAutomation, AccountRisk, RiskChoice
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    'CheckAccountsAutomationViewSet', 'CheckAccountExecutionViewSet',
    'AccountRiskViewSet', 'AccountCheckEngineViewSet',
]


class CheckAccountsAutomationViewSet(OrgBulkModelViewSet):
    model = AccountCheckAutomation
    filterset_fields = ('name',)
    search_fields = filterset_fields
    serializer_class = serializers.CheckAccountsAutomationSerializer


class CheckAccountExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_gatheraccountsexecution"),
        ("retrieve", "accounts.view_gatheraccountsexecution"),
        ("create", "accounts.add_gatheraccountsexecution"),
    )

    tp = AutomationTypes.gather_accounts

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


class AccountCheckEngineViewSet(OrgBulkModelViewSet):
    search_fields = ('name',)
    serializer_class = serializers.AccountCheckEngineSerializer
    rbac_perms = {
        'list': 'assets.view_accountcheckautomation',
    }

    def get_queryset(self):
        return [
            {
                'id': 1,
                'name': 'check_gathered_account',
                'display_name': '检查发现的账号',
                'description': '基于自动发现的账号结果进行检查分析，检查 用户组、公钥、sudoers 等信息'
            },
            {
                'id': 2,
                'name': 'check_account_secret',
                'display_name': '检查账号密码强弱',
                'description': '基于账号密码的安全性进行检查分析, 检查密码强度、泄露等信息'
            }
        ]
