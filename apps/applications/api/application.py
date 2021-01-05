# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet

from ..hands import IsOrgAdminOrAppUser
from .. import models, serializers


__all__ = ['ApplicationViewSet']


class ApplicationViewSet(OrgBulkModelViewSet):
    model = models.Application
    filter_fields = ('name', 'type', 'category')
    search_fields = filter_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ApplicationSerializer

