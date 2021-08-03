# -*- coding: utf-8 -*-
#
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import RetrieveAPIView
from django.shortcuts import get_object_or_404

from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser, IsSuperUser
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from assets.api import FilterAssetByNodeMixin
from rbac.permissions import RBACPermission
from ..models import Asset, Node, Platform
from .. import serializers
from ..tasks import (
    update_assets_hardware_info_manual, test_assets_connectivity_manual,
    test_system_users_connectivity_a_asset, push_system_users_a_asset
)
from ..filters import FilterAssetByNodeFilterBackend, LabelFilterBackend, IpInFilterBackend


logger = get_logger(__file__)
__all__ = [
    'AssetViewSet', 'AssetPlatformRetrieveApi',
    'AssetGatewayListApi', 'AssetPlatformViewSet',
    'AssetTaskCreateApi', 'AssetsTaskCreateApi',
]


class AssetViewSet(FilterAssetByNodeMixin, OrgBulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    model = Asset
    filterset_fields = {
        'hostname': ['exact'],
        'ip': ['exact'],
        'system_users__id': ['exact'],
        'platform__base': ['exact'],
        'is_active': ['exact'],
        'protocols': ['exact', 'icontains']
    }
    search_fields = ("hostname", "ip")
    ordering_fields = ("hostname", "ip", "port", "cpu_cores")
    serializer_classes = {
        'default': serializers.AssetSerializer,
    }
    extra_filter_backends = [FilterAssetByNodeFilterBackend, LabelFilterBackend, IpInFilterBackend]

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


class AssetPlatformRetrieveApi(RetrieveAPIView):
    queryset = Platform.objects.all()
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.PlatformSerializer

    def get_object(self):
        asset_pk = self.kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_pk)
        return asset.platform


class AssetPlatformViewSet(ModelViewSet):
    queryset = Platform.objects.all()
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.PlatformSerializer
    filterset_fields = ['name', 'base']
    search_fields = ['name']

    def get_permissions(self):
        if self.request.method.lower() in ['get', 'options']:
            self.permission_classes = (IsOrgAdmin,)
        return super().get_permissions()

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)


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
    permission_classes = (IsOrgAdmin,)

    def create(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        request.data['asset'] = pk
        request.data['assets'] = [pk]
        return super().create(request, *args, **kwargs)

    def perform_asset_task(self, serializer):
        data = serializer.validated_data
        action = data['action']
        if action not in ['push_system_user', 'test_system_user']:
            return
        asset = data['asset']
        system_users = data.get('system_users')
        if not system_users:
            system_users = asset.get_all_systemusers()
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
    permission_classes = (IsOrgAdmin,)


class AssetGatewayListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.GatewayWithAuthSerializer

    def get_queryset(self):
        asset_id = self.kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        if not asset.domain:
            return []
        queryset = asset.domain.gateways.filter(protocol='ssh')
        return queryset
