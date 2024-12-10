# -*- coding: utf-8 -*-
#
from django.db.models import Q, Count
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from operator import itemgetter
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.models import (
    CheckAccountAutomation,
    AccountRisk,
    RiskChoice,
    CheckAccountEngine,
    AutomationExecution,
)
from assets.models import Asset
from common.api import JMSModelViewSet
from common.utils import many_get
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    "CheckAccountAutomationViewSet",
    "CheckAccountExecutionViewSet",
    "AccountRiskViewSet",
    "CheckAccountEngineViewSet",
]

from ...risk_handlers import RiskHandler


class CheckAccountAutomationViewSet(OrgBulkModelViewSet):
    model = CheckAccountAutomation
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_class = serializers.CheckAccountAutomationSerializer


class CheckAccountExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_checkaccountexecution"),
        ("retrieve", "accounts.view_checkaccountsexecution"),
        ("create", "accounts.add_checkaccountexecution"),
        ("adhoc", "accounts.add_checkaccountexecution"),
        ("report", "accounts.view_checkaccountsexecution"),
    )
    ordering = ("-date_created",)
    tp = AutomationTypes.check_account

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(automation__type=self.tp)
        return queryset

    @action(methods=["get"], detail=False, url_path="adhoc")
    def adhoc(self, request, *args, **kwargs):
        asset_id = request.query_params.get("asset_id")
        if not asset_id:
            return Response(status=400, data={"asset_id": "This field is required."})

        get_object_or_404(Asset, pk=asset_id)
        execution = AutomationExecution()
        execution.snapshot = {
            "assets": [asset_id],
            "nodes": [],
            "type": AutomationTypes.check_account,
            "engines": ["check_account_secret"],
            "name": "Check asset risk: {} {}".format(asset_id, timezone.now()),
        }
        execution.save()
        execution.start()
        report = execution.manager.gen_report()
        return HttpResponse(report)


class AccountRiskViewSet(OrgBulkModelViewSet):
    model = AccountRisk
    search_fields = ("username", "asset")
    filterset_fields = ("risk", "status", "asset")
    serializer_classes = {
        "default": serializers.AccountRiskSerializer,
        "assets": serializers.AssetRiskSerializer,
        "handle": serializers.HandleRiskSerializer,
    }
    ordering_fields = ("asset", "risk", "status", "username", "date_created")
    ordering = ("status", "asset", "date_created")
    rbac_perms = {
        "sync_accounts": "assets.add_accountrisk",
        "assets": "accounts.view_accountrisk",
        "handle": "accounts.change_accountrisk",
    }

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed("PUT")

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    @action(methods=["get"], detail=False, url_path="assets")
    def assets(self, request, *args, **kwargs):
        annotations = {
            f"{risk[0]}_count": Count("id", filter=Q(risk=risk[0]))
            for risk in RiskChoice.choices
        }
        queryset = (
            AccountRisk.objects.select_related(
                "asset", "asset__platform"
            )  # 使用 select_related 来优化 asset 和 asset__platform 的查询
            .values(
                "asset__id", "asset__name", "asset__address", "asset__platform__name"
            )  # 添加需要的字段
            .annotate(risk_total=Count("id"))  # 计算风险总数
            .annotate(**annotations)  # 使用上面定义的 annotations 进行计数
        )
        return self.get_paginated_response_from_queryset(queryset)

    @action(methods=["post"], detail=False, url_path="handle")
    def handle(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)

        asset, username, act, risk = many_get(
            s.validated_data, ("asset", "username", "action", "risk")
        )
        handler = RiskHandler(asset=asset, username=username, request=self.request)
        data = handler.handle(act, risk)
        if not data:
            data = {"message": "Success"}
        return Response(data)


class CheckAccountEngineViewSet(JMSModelViewSet):
    search_fields = ("name",)
    serializer_class = serializers.CheckAccountEngineSerializer

    @staticmethod
    def init_if_need():
        data = [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "slug": "check_gathered_account",
                "name": "检查发现的账号",
                "comment": "基于自动发现的账号结果进行检查分析，检查 用户组、公钥、sudoers 等信息",
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "slug": "check_account_secret",
                "name": "检查账号密码强弱",
                "comment": "基于账号密码的安全性进行检查分析, 检查密码强度、泄露等信息",
            },
        ]

        model_cls = CheckAccountEngine
        if model_cls.objects.all().count() == 2:
            return

        for item in data:
            model_cls.objects.create(**item)

    def get_queryset(self):
        self.init_if_need()
        return CheckAccountEngine.objects.all()
