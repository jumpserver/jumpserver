# -*- coding: utf-8 -*-
#

from rest_framework.response import Response

from orgs.mixins import generics
from orgs.mixins.api import OrgBulkModelViewSet
from perms import serializers
from perms.filters import AssetPermissionFilter
from perms.models import AssetPermission
from perms.utils import get_permission_tree_metrics

__all__ = ['AssetPermissionViewSet', 'AssetPermissionTreeMetricsApi']


class AssetPermissionViewSet(OrgBulkModelViewSet):
    """
    资产授权列表的增删改查api
    """
    model = AssetPermission
    serializer_classes = {
        'default': serializers.AssetPermissionSerializer,
        'list': serializers.AssetPermissionListSerializer,
    }
    filterset_class = AssetPermissionFilter
    search_fields = ('name',)


class AssetPermissionTreeMetricsApi(generics.CreateAPIView):
    """Return direct/inherited permission counts for visible tree items."""

    model = AssetPermission
    serializer_class = serializers.PermissionTreeMetricsQuerySerializer
    rbac_perms = {
        'POST': 'perms.view_assetpermission',
    }

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        results = get_permission_tree_metrics(
            items=data['items'], metric=data['metric']
        )
        return Response({
            'metric': data['metric'],
            'results': results,
        })
