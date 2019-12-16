# -*- coding: utf-8 -*-
#

from ..serializers import UserGroupSerializer
from ..models import UserGroup
from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin


__all__ = ['UserGroupViewSet']


class UserGroupViewSet(OrgBulkModelViewSet):
    model = UserGroup
    filter_fields = ("name",)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
    serializer_class = UserGroupSerializer

