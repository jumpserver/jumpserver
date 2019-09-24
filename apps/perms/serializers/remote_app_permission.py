#  coding: utf-8
#

from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import RemoteAppPermission


__all__ = [
    'RemoteAppPermissionSerializer',
    'RemoteAppPermissionUpdateUserSerializer',
    'RemoteAppPermissionUpdateRemoteAppSerializer',
]


class RemoteAppPermissionSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = RemoteAppPermission
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'users', 'user_groups', 'remote_apps', 'system_users',
            'comment', 'is_active', 'date_start', 'date_expired', 'is_valid',
            'created_by', 'date_created',
        ]
        read_only_fields = ['created_by', 'date_created']


class RemoteAppPermissionUpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'users']


class RemoteAppPermissionUpdateRemoteAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'remote_apps']
