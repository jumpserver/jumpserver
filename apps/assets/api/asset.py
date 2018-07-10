# -*- coding: utf-8 -*-
#

import random

from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView
from rest_framework.pagination import LimitOffsetPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q

from common.mixins import IDInFilterMixin
from common.utils import get_logger
from ..hands import IsSuperUser, IsValidUser, IsSuperUserOrAppUser
from ..models import Asset, SystemUser, AdminUser, Node
from .. import serializers
from ..tasks import update_asset_hardware_info_manual, \
    test_asset_connectability_manual
from ..utils import LabelFilter


logger = get_logger(__file__)
__all__ = [
    'AssetViewSet', 'AssetListUpdateApi',
    'AssetRefreshHardwareApi', 'AssetAdminUserTestApi',
    'AssetGatewayApi'
]


class AssetViewSet(IDInFilterMixin, LabelFilter, BulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    filter_fields = ("hostname", "ip")
    search_fields = filter_fields
    ordering_fields = ("hostname", "ip", "port", "cpu_cores")
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsSuperUserOrAppUser,)

    def get_queryset(self):
        queryset = super().get_queryset()\
            .prefetch_related('labels', 'nodes')\
            .select_related('admin_user')
        admin_user_id = self.request.query_params.get('admin_user_id')
        node_id = self.request.query_params.get("node_id")
        show_current_asset = self.request.query_params.get("show_current_asset")

        if admin_user_id:
            admin_user = get_object_or_404(AdminUser, id=admin_user_id)
            queryset = queryset.filter(admin_user=admin_user)

        if node_id and show_current_asset:
            node = get_object_or_404(Node, id=node_id)
            if node.is_root():
                queryset = queryset.filter(
                    Q(nodes=node_id) | Q(nodes__isnull=True)
                ).distinct()
            else:
                queryset = queryset.filter(nodes=node).distinct()

        if node_id and not show_current_asset:
            node = get_object_or_404(Node, id=node_id)
            if node.is_root():
                queryset = Asset.objects.all()
            else:
                queryset = queryset.filter(
                    nodes__key__regex='^{}(:[0-9]+)*$'.format(node.key),
                ).distinct()
        return queryset


class AssetListUpdateApi(IDInFilterMixin, ListBulkCreateUpdateDestroyAPIView):
    """
    Asset bulk update api
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)


class AssetRefreshHardwareApi(generics.RetrieveAPIView):
    """
    Refresh asset hardware info
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        task = update_asset_hardware_info_manual.delay(asset)
        return Response({"task": task.id})


class AssetAdminUserTestApi(generics.RetrieveAPIView):
    """
    Test asset admin user connectivity
    """
    queryset = Asset.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        task = test_asset_connectability_manual.delay(asset)
        return Response({"task": task.id})


class AssetGatewayApi(generics.RetrieveAPIView):
    queryset = Asset.objects.all()
    permission_classes = (IsSuperUserOrAppUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)

        if asset.domain and \
                asset.domain.gateways.filter(protocol=asset.protocol).exists():
            gateway = random.choice(asset.domain.gateways.filter(protocol=asset.protocol))
            serializer = serializers.GatewayWithAuthSerializer(instance=gateway)
            return Response(serializer.data)
        else:
            return Response({"msg": "Not have gateway"}, status=404)