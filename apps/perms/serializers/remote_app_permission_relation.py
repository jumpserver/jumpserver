#  coding: utf-8
#
from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer
from ..models import RemoteAppPermission


__all__ = [
    'RemoteAppPermissionRemoteAppRelationSerializer',
    'RemoteAppPermissionAllRemoteAppSerializer',
    'RemoteAppPermissionUserRelationSerializer',
]


class RemoteAppPermissionRemoteAppRelationSerializer(serializers.ModelSerializer):
    remoteapp_display = serializers.ReadOnlyField()
    remoteapppermission_display = serializers.ReadOnlyField()

    class Meta:
        model = RemoteAppPermission.remote_apps.through
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'remoteapp', 'remoteapp_display', 'remoteapppermission', 'remoteapppermission_display'
        ]


class RemoteAppPermissionAllRemoteAppSerializer(serializers.Serializer):
    remoteapp = serializers.UUIDField(read_only=True, source='id')
    remoteapp_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'name']

    @staticmethod
    def get_remoteapp_display(obj):
        return str(obj)


class RemoteAppPermissionUserRelationSerializer(serializers.ModelSerializer):
    user_display = serializers.ReadOnlyField()
    remoteapppermission_display = serializers.ReadOnlyField()

    class Meta:
        model = RemoteAppPermission.users.through
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'user', 'user_display', 'remoteapppermission', 'remoteapppermission_display'
        ]
