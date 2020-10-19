# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet

from .. import models
from .. import serializers
from ..hands import IsOrgAdminOrAppUser

__all__ = [
    'ApplicationViewSet',
]


class ApplicationViewSet(OrgBulkModelViewSet):
    model = models.Application
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.ApplicationSerializer
