# -*- coding: utf-8 -*-
#

import django_filters
from rest_framework.decorators import action
from rest_framework.response import Response

from assets import serializers
from assets.filters import IpInFilterBackend, LabelFilterBackend, NodeFilterBackend
from assets.models import Asset, Gateway
from assets.tasks import (
    push_accounts_to_assets, test_assets_connectivity_manual,
    update_assets_hardware_info_manual, verify_accounts_connectivity,
)
from common.drf.filters import BaseFilterSet
from common.mixins.api import SuggestionMixin
from common.utils import get_logger
from orgs.mixins import generics
from orgs.mixins.api import OrgBulkModelViewSet
from ..mixin import NodeFilterMixin

logger = get_logger(__file__)
__all__ = [
    "AssetViewSet",
    "AssetTaskCreateApi",
    "AssetsTaskCreateApi",
    'AssetFilterSet'
]


class AssetFilterSet(BaseFilterSet):
    type = django_filters.CharFilter(field_name="platform__type", lookup_expr="exact")
    category = django_filters.CharFilter(field_name="platform__category", lookup_expr="exact")
    platform = django_filters.CharFilter(method='filter_platform')

    class Meta:
        model = Asset
        fields = [
            "id", "name", "address", "is_active",
            "type", "category", "platform"
        ]

    @staticmethod
    def filter_platform(queryset, name, value):
        if value.isdigit():
            return queryset.filter(platform_id=value)
        else:
            return queryset.filter(platform__name=value)


class AssetViewSet(SuggestionMixin, NodeFilterMixin, OrgBulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """

    model = Asset
    filterset_class = AssetFilterSet
    search_fields = ("name", "address")
    ordering_fields = ("name", "address")
    ordering = ("name",)
    serializer_classes = (
        ("default", serializers.AssetSerializer),
        ("retrieve", serializers.AssetDetailSerializer),
        ("suggestion", serializers.MiniAssetSerializer),
        ("platform", serializers.PlatformSerializer),
        ("gateways", serializers.GatewaySerializer),
    )
    rbac_perms = (
        ("match", "assets.match_asset"),
        ("platform", "assets.view_platform"),
        ("gateways", "assets.view_gateway"),
    )
    extra_filter_backends = [LabelFilterBackend, IpInFilterBackend, NodeFilterBackend]

    @action(methods=["GET"], detail=True, url_path="platform")
    def platform(self, *args, **kwargs):
        asset = self.get_object()
        serializer = self.get_serializer(asset.platform)
        return Response(serializer.data)

    @action(methods=["GET"], detail=True, url_path="gateways")
    def gateways(self, *args, **kwargs):
        asset = self.get_object()
        if not asset.domain:
            gateways = Gateway.objects.none()
        else:
            gateways = asset.domain.gateways
        return self.get_paginated_response_from_queryset(gateways)


class AssetsTaskMixin:
    def perform_assets_task(self, serializer):
        data = serializer.validated_data
        assets = data.get("assets", [])
        asset_ids = [asset.id for asset in assets]
        if data["action"] == "refresh":
            task = update_assets_hardware_info_manual.delay(asset_ids)
        else:
            task = test_assets_connectivity_manual.delay(asset_ids)
        return task

    def perform_create(self, serializer):
        task = self.perform_assets_task(serializer)
        self.set_task_to_serializer_data(serializer, task)

    def set_task_to_serializer_data(self, serializer, task):
        data = getattr(serializer, "_data", {})
        data["task"] = task.id
        setattr(serializer, "_data", data)


class AssetTaskCreateApi(AssetsTaskMixin, generics.CreateAPIView):
    model = Asset
    serializer_class = serializers.AssetTaskSerializer

    def create(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        request.data["asset"] = pk
        request.data["assets"] = [pk]
        return super().create(request, *args, **kwargs)

    def check_permissions(self, request):
        action = request.data.get("action")
        action_perm_require = {
            "refresh": "assets.refresh_assethardwareinfo",
            "push_account": "assets.push_assetsystemuser",
            "test": "assets.test_assetconnectivity",
            "test_account": "assets.test_assetconnectivity",
        }
        perm_required = action_perm_require.get(action)
        has = self.request.user.has_perm(perm_required)

        if not has:
            self.permission_denied(request)

    @staticmethod
    def perform_asset_task(serializer):
        data = serializer.validated_data
        if data["action"] not in ["push_system_user", "test_system_user"]:
            return

        asset = data["asset"]
        accounts = data.get("accounts")
        if not accounts:
            accounts = asset.accounts.all()

        asset_ids = [asset.id]
        account_ids = accounts.values_list("id", flat=True)
        if action == "push_account":
            task = push_accounts_to_assets.delay(account_ids, asset_ids)
        elif action == "test_account":
            task = verify_accounts_connectivity.delay(account_ids, asset_ids)
        else:
            task = None
        return task

    def perform_create(self, serializer):
        task = self.perform_asset_task(serializer)
        if not task:
            task = self.perform_assets_task(serializer)
        self.set_task_to_serializer_data(serializer, task)


class AssetsTaskCreateApi(AssetsTaskMixin, generics.CreateAPIView):
    model = Asset
    serializer_class = serializers.AssetsTaskSerializer

    def check_permissions(self, request):
        action = request.data.get("action")
        action_perm_require = {
            "refresh": "assets.refresh_assethardwareinfo",
        }
        perm_required = action_perm_require.get(action)
        has = self.request.user.has_perm(perm_required)
        if not has:
            self.permission_denied(request)
