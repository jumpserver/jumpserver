#  coding: utf-8
#

from rest_framework import serializers

from ..models import RemoteAppPermission

__all__ = [
    'RemoteAppPermissionSerializer',
]


class RemoteAppPermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = RemoteAppPermission
        fields = [
            'id', 'name', 'users', 'user_groups', 'remote_apps', 'comment',
            'is_active', 'date_start', 'date_expired', 'is_valid',
            'created_by', 'date_created', 'org_id'
        ]
