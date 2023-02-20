# -*- coding: utf-8 -*-
#

from orgs.mixins.api import OrgBulkModelViewSet
from ..models import UserGroup
from ..serializers import UserGroupSerializer

__all__ = ['UserGroupViewSet']


class UserGroupViewSet(OrgBulkModelViewSet):
    model = UserGroup
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_class = UserGroupSerializer
    ordering = ('name',)
