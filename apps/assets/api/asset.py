# -*- coding: utf-8 -*-
#

import uuid
import random

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView
from rest_framework.pagination import LimitOffsetPagination
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.core.cache import cache
from django.db.models import Q

from common.mixins import IDInCacheFilterMixin

from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from ..const import CACHE_KEY_ASSET_BULK_UPDATE_ID_PREFIX
from ..models import Asset, AdminUser, Node
from .. import serializers
from ..tasks import update_asset_hardware_info_manual, \
    test_asset_connectivity_manual
from ..utils import LabelFilter


logger = get_logger(__file__)
__all__ = [
    'AssetViewSet', 'AssetListUpdateApi',
    'AssetRefreshHardwareApi', 'AssetAdminUserTestApi',
    'AssetGatewayApi', 'AssetBulkUpdateSelectAPI'
]


class AssetViewSet(IDInCacheFilterMixin, LabelFilter, BulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    filter_fields = ("hostname", "ip")
    search_fields = filter_fields
    ordering_fields = ("hostname", "ip", "port", "cpu_cores")
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsOrgAdminOrAppUser,)

    def set_assets_node(self, assets):
        if not isinstance(assets, list):
            assets = [assets]
        node = Node.root()
        node_id = self.request.query_params.get('node_id')
        if node_id:
            node = get_object_or_none(Node, pk=node_id)
        node.assets.add(*assets)

    def perform_create(self, serializer):
        assets = serializer.save()
        self.set_assets_node(assets)

    def filter_node(self, queryset):
        node_id = self.request.query_params.get("node_id")
        if not node_id:
            return queryset

        node = get_object_or_404(Node, id=node_id)
        show_current_asset = self.request.query_params.get("show_current_asset") in ('1', 'true')

        if node.is_root() and show_current_asset:
            queryset = queryset.filter(
                Q(nodes=node_id) | Q(nodes__isnull=True)
            )
        elif node.is_root() and not show_current_asset:
            pass
        elif not node.is_root() and show_current_asset:
            queryset = queryset.filter(nodes=node)
        else:
            queryset = queryset.filter(
                nodes__key__regex='^{}(:[0-9]+)*$'.format(node.key),
            )
        return queryset

    def filter_admin_user_id(self, queryset):
        admin_user_id = self.request.query_params.get('admin_user_id')
        if not admin_user_id:
            return queryset
        admin_user = get_object_or_404(AdminUser, id=admin_user_id)
        queryset = queryset.filter(admin_user=admin_user)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_node(queryset)
        queryset = self.filter_admin_user_id(queryset)
        return queryset

    def get_queryset(self):
        queryset = super().get_queryset().distinct()
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset


class AssetListUpdateApi(IDInCacheFilterMixin, ListBulkCreateUpdateDestroyAPIView):
    """
    Asset bulk update api
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsOrgAdmin,)


class AssetBulkUpdateSelectAPI(APIView):
    permission_classes = (IsOrgAdmin,)

    def post(self, request, *args, **kwargs):
        assets_id = request.data.get('assets_id', '')
        if assets_id:
            spm = uuid.uuid4().hex
            key = CACHE_KEY_ASSET_BULK_UPDATE_ID_PREFIX.format(spm)
            cache.set(key, assets_id, 300)
            url = reverse_lazy('assets:asset-bulk-update') + '?spm=%s' % spm
            return Response({'url': url})
        error = _('Please select assets that need to be updated')
        return Response({'error': error}, status=400)


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
                asset.domain.gateways.filter(protocol=asset.protocol).exists():
            gateway = random.choice(asset.domain.gateways.filter(protocol=asset.protocol))
            serializer = serializers.GatewayWithAuthSerializer(instance=gateway)
            return Response(serializer.data)
        else:
            return Response({"msg": "Not have gateway"}, status=404)