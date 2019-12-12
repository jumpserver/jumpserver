# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet

from .. import models, serializers
from common.permissions import IsOrgAdmin


__all__ = ['DatabaseAppPermissionViewSet']


class DatabaseAppPermissionViewSet(OrgBulkModelViewSet):
    model = models.DatabaseAppPermission
    serializer_class = serializers.DatabaseAppPermissionSerializer
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
