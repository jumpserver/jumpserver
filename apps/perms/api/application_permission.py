# -*- coding: utf-8 -*-
#
from django.db.models import Q

from common.permissions import IsOrgAdmin
from orgs.mixins.api import OrgModelViewSet
from common.utils import get_object_or_none
from ..models import ApplicationPermission
from ..hands import (
    User, UserGroup, Asset, Node, SystemUser,
)
from .. import serializers


class ApplicationPermissionViewSet(OrgModelViewSet):
    """
    应用授权列表的增删改查API
    """
    model = ApplicationPermission
    serializer_class = serializers.ApplicationPermissionSerializer
    filter_fields = ['name']
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            "applications", "users", "user_groups", "system_users"
        )
        return queryset

