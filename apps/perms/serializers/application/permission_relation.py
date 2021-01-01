# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.mixins import BulkSerializerMixin
from common.drf.serializers import AdaptedBulkListSerializer
from perms.models import ApplicationPermission

__all__ = [
    'ApplicationPermissionUserRelationSerializer',
    'ApplicationPermissionUserGroupRelationSerializer',
    'ApplicationPermissionApplicationRelationSerializer',
    'ApplicationPermissionSystemUserRelationSerializer',
    'ApplicationPermissionAllApplicationSerializer',
    'ApplicationPermissionAllUserSerializer'
]


class RelationMixin(BulkSerializerMixin, serializers.Serializer):
    applicationpermission_display = serializers.ReadOnlyField()

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['applicationpermission', "applicationpermission_display"])
        return fields

    class Meta:
        list_serializer_class = AdaptedBulkListSerializer


class ApplicationPermissionUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    user_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = ApplicationPermission.users.through
        fields = [
            'id', 'user', 'user_display',
        ]


class ApplicationPermissionUserGroupRelationSerializer(RelationMixin, serializers.ModelSerializer):
    usergroup_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = ApplicationPermission.user_groups.through
        fields = [
            'id', 'usergroup', "usergroup_display",
        ]


class ApplicationPermissionApplicationRelationSerializer(RelationMixin, serializers.ModelSerializer):
    application_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = ApplicationPermission.applications.through
        fields = [
            'id', "application", "application_display",
        ]


class ApplicationPermissionSystemUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    systemuser_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = ApplicationPermission.system_users.through
        fields = [
            'id', 'systemuser', 'systemuser_display'
        ]


class ApplicationPermissionAllApplicationSerializer(serializers.Serializer):
    application = serializers.UUIDField(read_only=True, source='id')
    application_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'name']

    @staticmethod
    def get_application_display(obj):
        return str(obj)


class ApplicationPermissionAllUserSerializer(serializers.Serializer):
    user = serializers.UUIDField(read_only=True, source='id')
    user_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'username', 'name']

    @staticmethod
    def get_user_display(obj):
        return str(obj)
