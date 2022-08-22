# -*- coding: utf-8 -*-
#
from rest_framework.decorators import action
from rest_framework.response import Response
import django_filters

from common.drf.filters import BaseFilterSet
from common.utils import get_logger, get_object_or_none
from common.mixins.api import SuggestionMixin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from assets.models import Asset, Node, Gateway
from assets import serializers
from assets.tasks import (
    update_assets_hardware_info_manual, test_assets_connectivity_manual,
)
from assets.filters import NodeFilterBackend, LabelFilterBackend, IpInFilterBackend
from ..mixin import NodeFilterMixin

logger = get_logger(__file__)
__all__ = [
    'AssetViewSet', 'AssetTaskCreateApi', 'AssetsTaskCreateApi',
]


class AssetFilterSet(BaseFilterSet):
    type = django_filters.CharFilter(field_name='platform__type', lookup_expr='exact')
    category = django_filters.CharFilter(field_name='platform__category', lookup_expr='exact')

    class Meta:
        model = Asset
        fields = ['name', 'ip', 'is_active', 'type', 'category']


class AssetViewSet(SuggestionMixin, NodeFilterMixin, OrgBulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    model = Asset
    filterset_class = AssetFilterSet
    search_fields = ("name", "ip")
    ordering_fields = ("name", "ip", "port")
    ordering = ('name', )
    serializer_classes = (
        ('default', serializers.AssetSerializer),
        ('suggestion', serializers.MiniAssetSerializer),
        ('platform', serializers.PlatformSerializer),
        ('gateways', serializers.GatewayWithAuthSerializer)
    )
    rbac_perms = (
        ('match', 'assets.match_asset'),
        ('platform', 'assets.view_platform'),
        ('gateways', 'assets.view_gateway')
    )
    extra_filter_backends = [
        LabelFilterBackend,
        IpInFilterBackend,
        NodeFilterBackend
    ]

    def set_assets_node(self, assets):
        if not isinstance(assets, list):
            assets = [assets]
        node_id = self.request.query_params.get('node_id')
        if not node_id:
            return
        node = get_object_or_none(Node, pk=node_id)
        if not node:
            return
        node.assets.add(*assets)

    def perform_create(self, serializer):
        assets = serializer.save()
        self.set_assets_node(assets)

    @action(methods=['GET'], detail=True, url_path='platform')
    def platform(self, *args, **kwargs):
        asset = self.get_object()
        serializer = self.get_serializer(asset.platform)
        return Response(serializer.data)

    @action(methods=['GET'], detail=True, url_path='gateways')
    def gateways(self, *args, **kwargs):
        asset = self.get_object()
        if not asset.domain:
            gateways = Gateway.objects.none()
        else:
            gateways = asset.domain.gateways.filter(protocol='ssh')
        return self.get_paginated_response_from_queryset(gateways)


class AssetsTaskMixin:
    def perform_assets_task(self, serializer):
        data = serializer.validated_data
        action = data['action']
        assets = data.get('assets', [])
        if action == "refresh":
            task = update_assets_hardware_info_manual.delay(assets)
        else:
            # action == 'test':
            task = test_assets_connectivity_manual.delay(assets)
        return task

    def perform_create(self, serializer):
        task = self.perform_assets_task(serializer)
        self.set_task_to_serializer_data(serializer, task)

    def set_task_to_serializer_data(self, serializer, task):
        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)


class AssetTaskCreateApi(AssetsTaskMixin, generics.CreateAPIView):
    model = Asset
    serializer_class = serializers.AssetTaskSerializer

    def create(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        request.data['asset'] = pk
        request.data['assets'] = [pk]
        return super().create(request, *args, **kwargs)

    def check_permissions(self, request):
        action = request.data.get('action')
        action_perm_require = {
            'refresh': 'assets.refresh_assethardwareinfo',
            'push_system_user': 'assets.push_assetsystemuser',
            'test': 'assets.test_assetconnectivity',
            'test_system_user': 'assets.test_assetconnectivity'
        }
        perm_required = action_perm_require.get(action)
        has = self.request.user.has_perm(perm_required)

        if not has:
            self.permission_denied(request)

    def perform_asset_task(self, serializer):
        data = serializer.validated_data
        action = data['action']
        if action not in ['push_system_user', 'test_system_user']:
            return

        asset = data['asset']
        system_users = data.get('system_users')
        if not system_users:
            system_users = asset.get_all_system_users()
        if action == 'push_system_user':
            task = push_system_users_a_asset.delay(system_users, asset=asset)
        elif action == 'test_system_user':
            task = test_system_users_connectivity_a_asset.delay(system_users, asset=asset)
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
        action = request.data.get('action')
        action_perm_require = {
            'refresh': 'assets.refresh_assethardwareinfo',
        }
        perm_required = action_perm_require.get(action)
        has = self.request.user.has_perm(perm_required)
        if not has:
            self.permission_denied(request)


