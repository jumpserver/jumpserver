# -*- coding: utf-8 -*-
#
from perms.filters import AssetPermissionFilter
from perms.models import AssetPermission
from orgs.mixins.api import OrgBulkModelViewSet
from perms import serializers
from common.permissions import IsOrgAdmin


__all__ = [
    'AssetPermissionViewSet',
]


class AssetPermissionViewSet(OrgBulkModelViewSet):
    """
    资产授权列表的增删改查api
    """
    permission_classes = (IsOrgAdmin,)
    model = AssetPermission
    serializer_class = serializers.AssetPermissionSerializer
    filterset_class = AssetPermissionFilter
