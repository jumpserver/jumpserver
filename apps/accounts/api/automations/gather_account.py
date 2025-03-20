# -*- coding: utf-8 -*-
#
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.clickjacking import xframe_options_sameorigin
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AutomationTypes
from accounts.filters import GatheredAccountFilterSet, NodeFilterBackend
from accounts.models import GatherAccountsAutomation, AutomationExecution, Account
from accounts.models import GatheredAccount
from assets.models import Asset
from common.const import ConfirmOrIgnore
from common.utils.http import is_true
from orgs.mixins.api import OrgBulkModelViewSet
from .base import AutomationExecutionViewSet

__all__ = [
    "DiscoverAccountsAutomationViewSet",
    "DiscoverAccountsExecutionViewSet",
    "GatheredAccountViewSet",
]

from ...risk_handlers import RiskHandler


class DiscoverAccountsAutomationViewSet(OrgBulkModelViewSet):
    model = GatherAccountsAutomation
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_class = serializers.DiscoverAccountAutomationSerializer


class DiscoverAccountsExecutionViewSet(AutomationExecutionViewSet):
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
        queryset = queryset.filter(type=self.tp)
        return queryset

    @xframe_options_sameorigin
    @action(methods=["get"], detail=False, url_path="adhoc")
    def adhoc(self, request, *args, **kwargs):
        asset_id = request.query_params.get("asset_id")
        if not asset_id:
            return Response(status=400, data={"asset_id": "This field is required."})

        asset = get_object_or_404(Asset, pk=asset_id)
        execution = AutomationExecution()
        execution.snapshot = {
            "assets": [asset_id],
            "nodes": [],
            "type": "gather_accounts",
            "is_sync_account": False,
            "check_risk": True,
            "name": "Adhoc gather accounts: {}".format(asset.name),
        }
        execution.save()
        execution.start()
        report = execution.manager.gen_report()
        return HttpResponse(report)


class GatheredAccountViewSet(OrgBulkModelViewSet):
    model = GatheredAccount
    search_fields = ("username",)
    filterset_class = GatheredAccountFilterSet
    extra_filter_backends = [NodeFilterBackend]
    ordering = ("status",)
    serializer_classes = {
        "default": serializers.DiscoverAccountSerializer,
        "status": serializers.DiscoverAccountActionSerializer,
        "details": serializers.DiscoverAccountDetailsSerializer
    }
    rbac_perms = {
        "status": "assets.change_gatheredaccount",
        "details": "assets.view_gatheredaccount"
    }

    @action(methods=["put"], detail=False, url_path="status")
    def status(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        validated_data = serializer.validated_data
        ids = validated_data.get('ids', [])
        new_status = validated_data.get('status')
        updated_instances = GatheredAccount.objects.filter(id__in=ids).select_related('asset')
        if new_status == ConfirmOrIgnore.confirmed:
            GatheredAccount.sync_accounts(updated_instances)
            updated_instances.update(present=True)
        updated_instances.update(status=new_status)
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
