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
        mini_fields = ['id', 'name']
        small_fields = mini_fields + [
            'comment', 'is_active', 'date_start', 'date_expired', 'is_valid',
            'create_by', 'date_created'
        ]
        m2m_fields = [
            'users', 'user_groups', 'remote_apps', 'system_users',
        ]
        fields = small_fields + m2m_fields
        read_only_fields = ['created_by', 'date_created']


class RemoteAppPermissionUpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'users']


class RemoteAppPermissionUpdateRemoteAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'remote_apps']
