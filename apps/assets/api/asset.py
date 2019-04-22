# -*- coding: utf-8 -*-
#

import uuid
import random

from django.db.models import Q
from django.core.cache import cache
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView
from rest_framework.pagination import LimitOffsetPagination

from common.mixins import IDInFilterMixin, IDInCacheFiterMixin
from common.utils import get_logger, get_object_or_none
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from common.utils.export import BulkModelViewSetAndExportImportView

from .. import serializers
from ..utils import LabelFilter
from ..models import Asset, AdminUser, Node
from ..tasks import (
    update_asset_hardware_info_manual, test_asset_connectivity_manual
)


logger = get_logger(__file__)
__all__ = [
    'AssetViewSet', 'AssetListUpdateApi',
    'AssetRefreshHardwareApi', 'AssetAdminUserTestApi',
    'AssetGatewayApi', 'ExportCacheApi',
]


class AssetViewSet(IDInCacheFiterMixin, IDInFilterMixin, LabelFilter,
                   BulkModelViewSetAndExportImportView):
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
    csv_filename_prefix = 'assets'
    model = Asset

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
        if self.request.query_params.get('file') == 'csv':
            return queryset
        if not self.request.query_params.get('format') == 'csv':
            queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset

    def get_serializer_class(self):
        serializer = super().get_serializer_class()
        if self.request.query_params.get('format') == 'csv' and \
                (self.request.query_params.get('spm') == ''):
            serializer = serializers.AssetImportTemplateSerializer
        if self.request.query_params.get('file') == 'csv':
            serializer = serializers.AssetImportTemplateSerializer
        return serializer


class AssetListUpdateApi(IDInFilterMixin, ListBulkCreateUpdateDestroyAPIView):
    """
    Asset bulk update api
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsOrgAdmin,)


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


@method_decorator(csrf_exempt, name='dispatch')
class ExportCacheApi(APIView):

    def post(self, request, *args, **kwargs):
        objs_id = request.data.get('objs_id', [])
        spm = uuid.uuid4().hex
        if self.request.query_params.get('sourse') == 'assets':
            url = reverse_lazy('api-assets:asset-list')+'?spm=%s&format=csv' % spm
            if not objs_id:
                node_id = request.data.get('node_id', [])
                node = get_object_or_none(Node, id=node_id) if node_id else Node.root()
                assets = node.get_all_assets()
                for asset in assets:
                    objs_id.append(asset.id)
        if self.request.query_params.get('source') == 'admin_user':
            pass
        if self.request.query_params.get('source') == 'user':
            pass
        cache.set(spm, objs_id, 300)
        return JsonResponse({'redirect': url})