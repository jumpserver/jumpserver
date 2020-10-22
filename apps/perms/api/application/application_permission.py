# -*- coding: utf-8 -*-
#
from common.permissions import IsOrgAdmin
from orgs.mixins.api import OrgBulkModelViewSet
from perms.models import ApplicationPermission
from perms import serializers


class ApplicationPermissionViewSet(OrgBulkModelViewSet):
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

