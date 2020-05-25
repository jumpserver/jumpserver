# coding: utf-8
#
from perms.serializers.base import PermissionAllUserSerializer
from rest_framework import serializers

from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer

from .. import models

__all__ = [
    'DatabaseAppPermissionUserRelationSerializer',
    'DatabaseAppPermissionUserGroupRelationSerializer',
    'DatabaseAppPermissionAllUserSerializer',
    'DatabaseAppPermissionDatabaseAppRelationSerializer',
    'DatabaseAppPermissionAllDatabaseAppSerializer',
    'DatabaseAppPermissionSystemUserRelationSerializer',
]


class RelationMixin(BulkSerializerMixin, serializers.Serializer):
    databaseapppermission_display = serializers.ReadOnlyField()

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['databaseapppermission', "databaseapppermission_display"])
        return fields

    class Meta:
        list_serializer_class = AdaptedBulkListSerializer


class DatabaseAppPermissionUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    user_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = models.DatabaseAppPermission.users.through
        fields = [
            'id', 'user', 'user_display',
        ]


class DatabaseAppPermissionUserGroupRelationSerializer(RelationMixin, serializers.ModelSerializer):
    usergroup_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = models.DatabaseAppPermission.user_groups.through
        fields = [
            'id', 'usergroup', "usergroup_display",
        ]


class DatabaseAppPermissionAllUserSerializer(PermissionAllUserSerializer):
    class Meta(PermissionAllUserSerializer.Meta):
        pass


class DatabaseAppPermissionDatabaseAppRelationSerializer(RelationMixin, serializers.ModelSerializer):
    databaseapp_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = models.DatabaseAppPermission.database_apps.through
        fields = [
            'id', "databaseapp", "databaseapp_display",
        ]


class DatabaseAppPermissionAllDatabaseAppSerializer(serializers.Serializer):
    databaseapp = serializers.UUIDField(read_only=True, source='id')
    databaseapp_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'name']

    @staticmethod
    def get_databaseapp_display(obj):
        return str(obj)


class DatabaseAppPermissionSystemUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    systemuser_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = models.DatabaseAppPermission.system_users.through
        fields = [
            'id', 'systemuser', 'systemuser_display'
        ]
