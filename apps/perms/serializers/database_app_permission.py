# coding: utf-8
#

from rest_framework import serializers

from common.fields import StringManyToManyField
from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import models

__all__ = [
    'DatabaseAppPermissionSerializer', 'DatabaseAppPermissionListSerializer'
]


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


class DatabaseAppPermissionListSerializer(BulkOrgResourceModelSerializer):
    users = StringManyToManyField(many=True, read_only=True)
    user_groups = StringManyToManyField(many=True, read_only=True)
    database_apps = StringManyToManyField(many=True, read_only=True)
    system_users = StringManyToManyField(many=True, read_only=True)
    is_valid = serializers.BooleanField()
    is_expired = serializers.BooleanField()

    class Meta:
        model = models.DatabaseAppPermission
        fields = '__all__'
