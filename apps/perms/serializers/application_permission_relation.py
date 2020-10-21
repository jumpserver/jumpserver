# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from assets.models import Asset, Node
from ..models import ApplicationPermission
from users.models import User

__all__ = [
    'ApplicationPermissionUserRelationSerializer',
    'ApplicationPermissionUserGroupRelationSerializer',
    'ApplicationPermissionApplicationRelationSerializer',
    'ApplicationPermissionSystemUserRelationSerializer'
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

