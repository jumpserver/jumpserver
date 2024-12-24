# -*- coding: utf-8 -*-
#
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.filters import GatheredAccountFilterSet
from accounts.models import GatherAccountsAutomation, AutomationExecution, Account
from accounts.models import GatheredAccount
from assets.models import Asset
from common.utils.http import is_true
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    "GatherAccountsAutomationViewSet",
    "GatherAccountsExecutionViewSet",
    "GatheredAccountViewSet",
]

from ...risk_handlers import RiskHandler


class GatherAccountsAutomationViewSet(OrgBulkModelViewSet):
    model = GatherAccountsAutomation
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_class = serializers.GatherAccountAutomationSerializer


class GatherAccountsExecutionViewSet(AutomationExecutionViewSet):
    rbac_perms = (
        ("list", "accounts.view_gatheraccountsexecution"),
        ("retrieve", "accounts.view_gatheraccountsexecution"),
        ("create", "accounts.add_gatheraccountsexecution"),
        ("adhoc", "accounts.add_gatheraccountsexecution"),
        ("report", "accounts.view_gatheraccountsexecution"),
    )

    tp = AutomationTypes.gather_accounts

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
            "type": "gather_accounts",
            "is_sync_account": False,
            "check_risk": True,
            "name": "Adhoc gather accounts: {}".format(asset_id),
        }
        execution.save()
        execution.start()
        report = execution.manager.gen_report()
        return HttpResponse(report)


class GatheredAccountViewSet(OrgBulkModelViewSet):
    model = GatheredAccount
    search_fields = ("username",)
    filterset_class = GatheredAccountFilterSet
    ordering = ("status",)
    serializer_classes = {
        "default": serializers.GatheredAccountSerializer,
        "status": serializers.GatheredAccountActionSerializer,
        "details": serializers.GatheredAccountDetailsSerializer
    }
    rbac_perms = {
        "status": "assets.change_gatheredaccount",
        "details": "assets.view_gatheredaccount"
    }

    @action(methods=["put"], detail=False, url_path="status")
    def status(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        new_status = request.data.get("status")
        updated_instances = GatheredAccount.objects.filter(id__in=ids)
        updated_instances.update(status=new_status)
        if new_status == "confirmed":
            GatheredAccount.sync_accounts(updated_instances)

        return Response(status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        request = self.request
        params = request.query_params
        is_delete_remote = params.get("is_delete_remote")
        is_delete_account = params.get("is_delete_account")
        asset_id = params.get("asset")
        username = params.get("username")
        if is_true(is_delete_remote):
            self._delete_remote(asset_id, username)
        if is_true(is_delete_account):
            account = get_object_or_404(Account, username=username, asset_id=asset_id)
            account.delete()
        super().perform_destroy(instance)

    def _delete_remote(self, asset_id, username):
        asset = get_object_or_404(Asset, pk=asset_id)
        handler = RiskHandler(asset, username, request=self.request)
        handler.handle_delete_remote()

    @action(methods=["get"], detail=True, url_path="details")
    def details(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        account = get_object_or_404(GatheredAccount, pk=pk)
        serializer = self.get_serializer(account.detail)
        return Response(data=serializer.data)
