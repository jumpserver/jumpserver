# -*- coding: utf-8 -*-
#
import django_filters
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.tasks import push_accounts_to_assets, verify_accounts_connectivity
from assets import serializers
from assets.filters import IpInFilterBackend, LabelFilterBackend, NodeFilterBackend
from assets.models import Asset, Gateway
from assets.tasks import (
    test_assets_connectivity_manual,
    update_assets_hardware_info_manual
)
from common.api import SuggestionMixin
from common.drf.filters import BaseFilterSet
from common.utils import get_logger
from orgs.mixins import generics
from orgs.mixins.api import OrgBulkModelViewSet
from ..mixin import NodeFilterMixin

logger = get_logger(__file__)
__all__ = [
    "AssetViewSet", "AssetTaskCreateApi",
    "AssetsTaskCreateApi", 'AssetFilterSet'
]


class AssetFilterSet(BaseFilterSet):
    type = django_filters.CharFilter(field_name="platform__type", lookup_expr="exact")
    category = django_filters.CharFilter(field_name="platform__category", lookup_expr="exact")
    platform = django_filters.CharFilter(method='filter_platform')
    labels = django_filters.CharFilter(method='filter_labels')

    class Meta:
        model = Asset
        fields = [
            "id", "name", "address", "is_active", "labels",
            "type", "category", "platform"
        ]

    @staticmethod
    def filter_platform(queryset, name, value):
        if value.isdigit():
            return queryset.filter(platform_id=value)
        else:
            return queryset.filter(platform__name=value)

    @staticmethod
    def filter_labels(queryset, name, value):
        if ':' in value:
            n, v = value.split(':', 1)
            queryset = queryset.filter(labels__name=n, labels__value=v)
        else:
            queryset = queryset.filter(Q(labels__name=value) | Q(labels__value=value))
        return queryset


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
        ("platform", serializers.PlatformSerializer),
        ("suggestion", serializers.MiniAssetSerializer),
        ("gateways", serializers.GatewaySerializer),
    )
    rbac_perms = (
        ("match", "assets.match_asset"),
        ("platform", "assets.view_platform"),
        ("gateways", "assets.view_gateway"),
    )
    extra_filter_backends = [LabelFilterBackend, IpInFilterBackend, NodeFilterBackend]

    def get_serializer_class(self):
        cls = super().get_serializer_class()
        if self.action == "retrieve":
            name = cls.__name__.replace("Serializer", "DetailSerializer")
            retrieve_cls = type(name, (serializers.DetailMixin, cls), {})
            return retrieve_cls
        return cls

    @action(methods=["GET"], detail=True, url_path="platform")
    def platform(self, *args, **kwargs):
        asset = super().get_object()
        serializer = super().get_serializer(instance=asset.platform)
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
        action_perm_require = {
            "refresh": "assets.refresh_assethardwareinfo",
            "push_account": "accounts.add_pushaccountexecution",
            "test": "assets.test_assetconnectivity",
            "test_account": "assets.test_account",
        }
        _action = request.data.get("action")
        perm_required = action_perm_require.get(_action)
        has = self.request.user.has_perm(perm_required)

        if not has:
            self.permission_denied(request)

    @staticmethod
    def perform_asset_task(serializer):
        data = serializer.validated_data
        if data["action"] not in ["push_account", "test_account"]:
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
        action_perm_require = {
            "refresh": "assets.refresh_assethardwareinfo",
        }
        _action = request.data.get("action")
        perm_required = action_perm_require.get(_action)
        has = self.request.user.has_perm(perm_required)
        if not has:
            self.permission_denied(request)
