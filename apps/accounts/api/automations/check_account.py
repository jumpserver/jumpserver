# -*- coding: utf-8 -*-
#

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import AccountCheckAutomation
from accounts.models import AccountRisk
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
    search_fields = ('username',)
    serializer_classes = {
        'default': serializers.AccountRiskSerializer,
    }
    rbac_perms = {
        'sync_accounts': 'assets.add_AccountRisk',
    }


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
                'description': '基于自动发现的账号结果进行检查分析 '
            },
            {
                'id': 2,
                'name': 'check_account_secret',
                'display_name': '检查账号密码强弱',
                'description': '基于账号密码的安全性进行检查分析'
            }
        ]
