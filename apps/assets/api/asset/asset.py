# -*- coding: utf-8 -*-
#
from collections import defaultdict

import django_filters
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from accounts.tasks import push_accounts_to_assets_task, verify_accounts_connectivity_task
from assets import serializers
from assets.exceptions import NotSupportedTemporarilyError
from assets.filters import IpInFilterBackend, NodeFilterBackend
from assets.models import Asset, Gateway, Platform, Protocol
from assets.tasks import test_assets_connectivity_manual, update_assets_hardware_info_manual
from common.api import SuggestionMixin
from common.drf.filters import BaseFilterSet, AttrRulesFilterBackend
from common.utils import get_logger, is_uuid
from orgs.mixins import generics
from orgs.mixins.api import OrgBulkModelViewSet
from ...notifications import BulkUpdatePlatformSkipAssetUserMsg

logger = get_logger(__file__)
__all__ = [
    "AssetViewSet", "AssetTaskCreateApi",
    "AssetsTaskCreateApi", 'AssetFilterSet',
]


class AssetFilterSet(BaseFilterSet):
    platform = django_filters.CharFilter(method='filter_platform')
    domain = django_filters.CharFilter(method='filter_domain')
    type = django_filters.CharFilter(field_name="platform__type", lookup_expr="exact")
    category = django_filters.CharFilter(field_name="platform__category", lookup_expr="exact")
    protocols = django_filters.CharFilter(method='filter_protocols')
    domain_enabled = django_filters.BooleanFilter(
        field_name="platform__domain_enabled", lookup_expr="exact"
    )
    ping_enabled = django_filters.BooleanFilter(
        field_name="platform__automation__ping_enabled", lookup_expr="exact"
    )
    gather_facts_enabled = django_filters.BooleanFilter(
        field_name="platform__automation__gather_facts_enabled", lookup_expr="exact"
    )
    change_secret_enabled = django_filters.BooleanFilter(
        field_name="platform__automation__change_secret_enabled", lookup_expr="exact"
    )
    push_account_enabled = django_filters.BooleanFilter(
        field_name="platform__automation__push_account_enabled", lookup_expr="exact"
    )
    verify_account_enabled = django_filters.BooleanFilter(
        field_name="platform__automation__verify_account_enabled", lookup_expr="exact"
    )
    gather_accounts_enabled = django_filters.BooleanFilter(
        field_name="platform__automation__gather_accounts_enabled", lookup_expr="exact"
    )

    class Meta:
        model = Asset
        fields = [
            "id", "name", "address", "is_active",
            "type", "category", "platform",
        ]

    @staticmethod
    def filter_platform(queryset, name, value):
        if value.isdigit():
            return queryset.filter(platform_id=value)
        else:
            return queryset.filter(platform__name=value)

    @staticmethod
    def filter_domain(queryset, name, value):
        if is_uuid(value):
            return queryset.filter(domain_id=value)
        else:
            return queryset.filter(domain__name__contains=value)

    @staticmethod
    def filter_protocols(queryset, name, value):
        value = value.split(',')
        return queryset.filter(protocols__name__in=value).distinct()


class AssetViewSet(SuggestionMixin, OrgBulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    model = Asset
    filterset_class = AssetFilterSet
    search_fields = ("name", "address", "comment")
    ordering = ('name',)
    ordering_fields = ('name', 'address', 'connectivity', 'platform', 'date_updated', 'date_created')
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
        ("spec_info", "assets.view_asset"),
        ("gathered_info", "assets.view_asset"),
        ("sync_platform_protocols", "assets.change_asset"),
    )
    extra_filter_backends = [
        IpInFilterBackend,
        NodeFilterBackend, AttrRulesFilterBackend
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        if queryset.model is not Asset:
            queryset = queryset.select_related('asset_ptr')
        return queryset

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

    @action(methods=['post'], detail=False, url_path='sync-platform-protocols')
    def sync_platform_protocols(self, request, *args, **kwargs):
        platform_id = request.data.get('platform_id')
        platform = get_object_or_404(Platform, pk=platform_id)
        assets = platform.assets.all()

        platform_protocols = {
            p['name']: p['port']
            for p in platform.protocols.values('name', 'port')
        }
        asset_protocols_map = defaultdict(set)
        protocols = assets.prefetch_related('protocols').values_list(
            'id', 'protocols__name'
        )
        for asset_id, protocol in protocols:
            asset_id = str(asset_id)
            asset_protocols_map[asset_id].add(protocol)
        objs = []
        for asset_id, protocols in asset_protocols_map.items():
            protocol_names = set(platform_protocols) - protocols
            if not protocol_names:
                continue
            for name in protocol_names:
                objs.append(
                    Protocol(
                        name=name,
                        port=platform_protocols[name],
                        asset_id=asset_id,
                    )
                )
        Protocol.objects.bulk_create(objs)
        return Response(status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if request.path.find('/api/v1/assets/assets/') > -1:
            error = _('Cannot create asset directly, you should create a host or other')
            return Response({'error': error}, status=400)
        return super().create(request, *args, **kwargs)

    def filter_bulk_update_data(self):
        bulk_data = []
        skip_assets = []
        for data in self.request.data:
            pk = data.get('id')
            platform = data.get('platform')
            if not platform:
                bulk_data.append(data)
                continue
            asset = get_object_or_404(Asset, pk=pk)
            platform = get_object_or_404(Platform, **platform)
            if platform.type == asset.type:
                bulk_data.append(data)
                continue
            skip_assets.append(asset)
        return bulk_data, skip_assets

    def bulk_update(self, request, *args, **kwargs):
        bulk_data, skip_assets = self.filter_bulk_update_data()
        request._full_data = bulk_data
        response = super().bulk_update(request, *args, **kwargs)
        if response.status_code == HTTP_200_OK and skip_assets:
            user = request.user
            BulkUpdatePlatformSkipAssetUserMsg(user, skip_assets).publish()
        return response


class AssetsTaskMixin:
    def perform_assets_task(self, serializer):
        data = serializer.validated_data
        assets = data.get("assets", [])

        if data["action"] == "refresh":
            task = update_assets_hardware_info_manual(assets)
        else:
            asset = assets[0]
            if not asset.auto_config['ansible_enabled'] or \
                    not asset.auto_config['ping_enabled']:
                raise NotSupportedTemporarilyError()
            task = test_assets_connectivity_manual(assets)
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
            "push_account": "accounts.push_account",
            "test": "assets.test_assetconnectivity",
            "test_account": "accounts.verify_account",
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

        account_ids = accounts.values_list('id', flat=True)
        account_ids = [str(_id) for _id in account_ids]
        if action == "push_account":
            task = push_accounts_to_assets_task.delay(account_ids)
        elif action == "test_account":
            task = verify_accounts_connectivity_task.delay(account_ids)
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
