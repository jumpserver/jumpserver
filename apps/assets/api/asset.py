# -*- coding: utf-8 -*-
#

import random

from rest_framework import generics
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from orgs.mixins.api import OrgBulkModelViewSet
from ..models import Asset, AdminUser, Node
from .. import serializers
from ..tasks import update_asset_hardware_info_manual, \
    test_asset_connectivity_manual
from ..filters import AssetByNodeFilterBackend, LabelFilterBackend


logger = get_logger(__file__)
__all__ = [
    'AssetViewSet',
    'AssetRefreshHardwareApi', 'AssetAdminUserTestApi',
    'AssetGatewayApi',
]


class AssetViewSet(OrgBulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    filter_fields = ("hostname", "ip", "systemuser__id", "admin_user__id")
    search_fields = ("hostname", "ip")
    ordering_fields = ("hostname", "ip", "port", "cpu_cores")
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
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

    def filter_admin_user_id(self, queryset):
        admin_user_id = self.request.query_params.get('admin_user_id')
        if not admin_user_id:
            return queryset
        admin_user = get_object_or_404(AdminUser, id=admin_user_id)
        queryset = queryset.filter(admin_user=admin_user)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_admin_user_id(queryset)
        return queryset


class AssetRefreshHardwareApi(generics.RetrieveAPIView):
    """
    Refresh asset hardware info
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        task = update_asset_hardware_info_manual.delay(asset)
        return Response({"task": task.id})


class AssetAdminUserTestApi(generics.RetrieveAPIView):
    """
    Test asset admin user assets_connectivity
    """
    queryset = Asset.objects.all()
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.TaskIDSerializer

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        task = test_asset_connectivity_manual.delay(asset)
        return Response({"task": task.id})


class AssetGatewayApi(generics.RetrieveAPIView):
    queryset = Asset.objects.all()
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.GatewayWithAuthSerializer

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)

        if asset.domain and \
                asset.domain.gateways.filter(protocol='ssh').exists():
            gateway = random.choice(asset.domain.gateways.filter(protocol='ssh'))
            serializer = serializers.GatewayWithAuthSerializer(instance=gateway)
            return Response(serializer.data)
        else:
            return Response({"msg": "Not have gateway"}, status=404)