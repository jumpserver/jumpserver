# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet

from .. import models, serializers
from common.permissions import IsOrgAdmin


__all__ = ['K8sAppPermissionViewSet']


class K8sAppPermissionViewSet(OrgBulkModelViewSet):
    model = models.K8sAppPermission
    serializer_classes = {
        'default': serializers.K8sAppPermissionSerializer,
        'display': serializers.K8sAppPermissionListSerializer
    }
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
