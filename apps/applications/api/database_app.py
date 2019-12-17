# coding: utf-8
# 

from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics

from .. import models
from .. import serializers
from ..hands import IsOrgAdmin, IsAppUser

__all__ = [
    'DatabaseAppViewSet',
    'DatabaseAppConnectionInfoApi',
]


class DatabaseAppViewSet(OrgBulkModelViewSet):
    model = models.DatabaseApp
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.DatabaseAppSerializer


class DatabaseAppConnectionInfoApi(generics.RetrieveAPIView):
    model = models.DatabaseApp
    permission_classes = (IsAppUser,)
    serializer_class = serializers.DatabaseAppConnectionInfoSerializer
