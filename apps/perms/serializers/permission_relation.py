# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.serializers import BulkSerializerMixin
from perms.models import AssetPermission

__all__ = [
    'AssetPermissionUserRelationSerializer',
    'AssetPermissionUserGroupRelationSerializer',
    "AssetPermissionAssetRelationSerializer",
    'AssetPermissionNodeRelationSerializer',
    'AssetPermissionAllAssetSerializer',
    'AssetPermissionAllUserSerializer',
]


class CurrentAssetPermission(object):
    permission = None

    def set_context(self, serializer_field):
        self.permission = serializer_field.context['permission']

    def __call__(self):
        return self.permission


class RelationMixin(BulkSerializerMixin, serializers.Serializer):
    assetpermission_display = serializers.ReadOnlyField()

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['assetpermission', "assetpermission_display"])
        return fields


class AssetPermissionUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    user_display = serializers.ReadOnlyField()

    class Meta:
        model = AssetPermission.users.through
        fields = [
            'id', 'user', 'user_display',
        ]


class AssetPermissionAllUserSerializer(serializers.Serializer):
    user = serializers.UUIDField(read_only=True, source='id')
    user_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'username', 'name']

    @staticmethod
    def get_user_display(obj):
        return str(obj)


class AssetPermissionUserGroupRelationSerializer(RelationMixin, serializers.ModelSerializer):
    usergroup_display = serializers.ReadOnlyField()

    class Meta:
        model = AssetPermission.user_groups.through
        fields = [
            'id', 'usergroup', "usergroup_display",
        ]


class AssetPermissionAssetRelationSerializer(RelationMixin, serializers.ModelSerializer):
    asset_display = serializers.ReadOnlyField()

    class Meta:
        model = AssetPermission.assets.through
        fields = [
            'id', "asset", "asset_display",
        ]


class AssetPermissionAllAssetSerializer(serializers.Serializer):
    asset = serializers.UUIDField(read_only=True, source='id')
    asset_display = serializers.SerializerMethodField()

    class Meta:
        only_fields = ['id', 'name', 'address']

    @staticmethod
    def get_asset_display(obj):
        return str(obj)


class AssetPermissionNodeRelationSerializer(RelationMixin, serializers.ModelSerializer):
    node_display = serializers.CharField(source='node.full_value', read_only=True)

    class Meta:
        model = AssetPermission.nodes.through
        fields = [
            'id', 'node', "node_display",
        ]
