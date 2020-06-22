# -*- coding: utf-8 -*-
#

from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import RetrieveAPIView
from django.shortcuts import get_object_or_404

from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser, IsSuperUser
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from ..models import Asset, Node, Platform
from .. import serializers
from ..tasks import (
    update_asset_hardware_info_manual, test_asset_connectivity_manual
)
from ..filters import AssetByNodeFilterBackend, LabelFilterBackend


logger = get_logger(__file__)
__all__ = [
    'AssetViewSet', 'AssetPlatformRetrieveApi',
    'AssetGatewayListApi', 'AssetPlatformViewSet',
    'AssetTaskCreateApi',
]


class AssetViewSet(OrgBulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    model = Asset
    filter_fields = (
        "hostname", "ip", "systemuser__id", "admin_user__id", "platform__base",
        "is_active"
    )
    search_fields = ("hostname", "ip")
    ordering_fields = ("hostname", "ip", "port", "cpu_cores")
    serializer_classes = {
        'default': serializers.AssetSerializer,
        'display': serializers.AssetDisplaySerializer,
    }
    permission_classes = (IsOrgAdminOrAppUser,)
    extra_filter_backends = [AssetByNodeFilterBackend, LabelFilterBackend]

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
    filter_fields = ['name', 'base']
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


class AssetTaskCreateApi(generics.CreateAPIView):
    model = Asset
    serializer_class = serializers.AssetTaskSerializer
    permission_classes = (IsOrgAdmin,)

    def get_object(self):
        pk = self.kwargs.get("pk")
        instance = get_object_or_404(Asset, pk=pk)
        return instance

    def perform_create(self, serializer):
        asset = self.get_object()
        action = serializer.validated_data["action"]
        if action == "refresh":
            task = update_asset_hardware_info_manual.delay(asset)
        else:
            task = test_asset_connectivity_manual.delay(asset)
        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)


class AssetGatewayListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.GatewayWithAuthSerializer
    model = Asset

    def get_queryset(self):
        asset_id = self.kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        if not asset.domain:
            return []
        queryset = asset.domain.gateways.filter(protocol='ssh')
        return queryset
