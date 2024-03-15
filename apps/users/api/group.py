# -*- coding: utf-8 -*-
#

from orgs.mixins.api import OrgBulkModelViewSet
from ..models import UserGroup
from ..serializers import UserGroupSerializer, UserGroupListSerializer

__all__ = ['UserGroupViewSet']


class UserGroupViewSet(OrgBulkModelViewSet):
    model = UserGroup
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_classes = {
        'default': UserGroupSerializer,
        'list': UserGroupListSerializer,
    }
    ordering = ('name',)
