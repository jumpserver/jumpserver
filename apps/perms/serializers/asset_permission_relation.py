# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from assets.models import Asset, Node
from ..models import AssetPermission

__all__ = [
    'AssetPermissionUserRelationSerializer',
    'AssetPermissionUserGroupRelationSerializer',
    "AssetPermissionAssetRelationSerializer",
    'AssetPermissionNodeRelationSerializer',
    'AssetPermissionSystemUserRelationSerializer',
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

    class Meta:
        list_serializer_class = AdaptedBulkListSerializer


class AssetPermissionUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    user_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = AssetPermission.users.through
        fields = [
            'id', 'user', 'user_display',
        ]


class AssetPermissionAllUserSerializer(serializers.ModelSerializer):
    user = serializers.UUIDField(read_only=True, source='id')
    user_display = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        only_fields = ['id', 'username', 'name']
        fields = ['user', 'user_display']

    @staticmethod
    def get_user_display(obj):
        return str(obj)


class AssetPermissionUserGroupRelationSerializer(RelationMixin, serializers.ModelSerializer):
    usergroup_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = AssetPermission.user_groups.through
        fields = [
            'id', 'usergroup', "usergroup_display",
        ]


class AssetPermissionAssetRelationSerializer(RelationMixin, serializers.ModelSerializer):
    asset_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = AssetPermission.assets.through
        fields = [
            'id', "asset", "asset_display",
        ]


class AssetPermissionAllAssetSerializer(serializers.ModelSerializer):
    asset = serializers.UUIDField(read_only=True, source='id')
    asset_display = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        only_fields = ['id', 'hostname', 'ip']
        fields = ['asset', 'asset_display']

    @staticmethod
    def get_asset_display(obj):
        return str(obj)


class AssetPermissionNodeRelationSerializer(RelationMixin, serializers.ModelSerializer):
    node_display = serializers.SerializerMethodField()

    class Meta(RelationMixin.Meta):
        model = AssetPermission.nodes.through
        fields = [
            'id', 'node', "node_display",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = Node.tree()

    def get_node_display(self, obj):
        if hasattr(obj, 'node_key'):
            return self.tree.get_node_full_tag(obj.node_key)
        else:
            return obj.node.full_value


class AssetPermissionSystemUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    systemuser_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = AssetPermission.system_users.through
        fields = [
            'id', 'systemuser', 'systemuser_display'
        ]
