# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from ..models import AssetPermission

__all__ = ['AssetPermissionUserSerializer']


class CurrentAssetPermission(object):
    permission = None

    def set_context(self, serializer_field):
        self.permission = serializer_field.context['permission']

    def __call__(self):
        return self.permission


class RelationMixin(serializers.Serializer):
    assetpermission = serializers.HiddenField(
        default=CurrentAssetPermission()
    )

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.append('assetpermission')
        return fields


class AssetPermissionUserSerializer(RelationMixin, serializers.ModelSerializer):
    user_display = serializers.StringRelatedField(source='user')

    class Meta:
        model = AssetPermission.users.through
        fields = [
            'id', 'user', 'user_display',
        ]


class AssetPermissionUserGroupSerializer(RelationMixin, serializers.ModelSerializer):
    usergroup_display = serializers.StringRelatedField(source="usergroup")

    class Meta:
        model = AssetPermission.user_groups.through
        fields = [
            'id', 'usergroup', "usergroup_display"
        ]


class AssetPermissionAssetSerializer(RelationMixin, serializers.ModelSerializer):
    asset = serializers.StringRelatedField()

    class Meta:
        model = AssetPermission.assets.through
        fields = [
            'id', 'asset_id',
            "asset"
        ]
