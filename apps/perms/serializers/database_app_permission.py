# coding: utf-8
#

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import models

__all__ = ['DatabaseAppPermissionSerializer']


class DatabaseAppPermissionSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = models.DatabaseAppPermission
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'users', 'user_groups',
            'database_apps', 'system_users', 'comment', 'is_active',
            'date_start', 'date_expired', 'is_valid',
            'created_by', 'date_created'
        ]
        read_only_fields = ['created_by', 'date_created']
