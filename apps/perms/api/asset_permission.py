# -*- coding: utf-8 -*-
#
from perms.filters import AssetPermissionFilter
from perms.models import AssetPermission
from orgs.mixins.api import OrgBulkModelViewSet
from perms import serializers


__all__ = ['AssetPermissionViewSet']


class AssetPermissionViewSet(OrgBulkModelViewSet):
    """
    资产授权列表的增删改查api
    """
    model = AssetPermission
    serializer_class = serializers.AssetPermissionSerializer
    filterset_class = AssetPermissionFilter
    search_fields = ('name',)
    ordering_fields = ('name',)
    ordering = ('name', )
