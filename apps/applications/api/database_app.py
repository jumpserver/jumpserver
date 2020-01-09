# coding: utf-8
# 

from orgs.mixins.api import OrgBulkModelViewSet

from .. import models
from .. import serializers
from ..hands import IsOrgAdminOrAppUser

__all__ = [
    'DatabaseAppViewSet',
]


class DatabaseAppViewSet(OrgBulkModelViewSet):
    model = models.DatabaseApp
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.DatabaseAppSerializer
