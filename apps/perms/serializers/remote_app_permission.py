#  coding: utf-8
#

from rest_framework import serializers

from common.fields import StringManyToManyField
from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import RemoteAppPermission


__all__ = [
    'RemoteAppPermissionSerializer',
    'RemoteAppPermissionUpdateUserSerializer',
    'RemoteAppPermissionUpdateRemoteAppSerializer',
    'RemoteAppPermissionListSerializer',
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


class RemoteAppPermissionListSerializer(BulkOrgResourceModelSerializer):
    users = StringManyToManyField(many=True, read_only=True)
    user_groups = StringManyToManyField(many=True, read_only=True)
    remote_apps = StringManyToManyField(many=True, read_only=True)
    system_users = StringManyToManyField(many=True, read_only=True)
    is_valid = serializers.BooleanField()
    is_expired = serializers.BooleanField()

    class Meta:
        model = RemoteAppPermission
        fields = '__all__'


class RemoteAppPermissionUpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'users']


class RemoteAppPermissionUpdateRemoteAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'remote_apps']
