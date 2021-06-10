# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.drf.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import AuthBook, Asset
from ..backends import AssetUserManager

from .base import ConnectivitySerializer, AuthSerializerMixin


__all__ = [
    'AssetUserWriteSerializer', 'AssetUserReadSerializer',
    'AssetUserAuthInfoSerializer', 'AssetUserPushSerializer',
]


class AssetUserWriteSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = AuthBook
        list_serializer_class = AdaptedBulkListSerializer
        fields_mini = ['id', 'username']
        fields_write_only = ['password', 'private_key', "public_key"]
        fields_small = fields_mini + fields_write_only + ['comment']
        fields_fk = ['asset']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'username': {'required': True},
            'password': {'write_only': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }

    def create(self, validated_data):
        if not validated_data.get("name") and validated_data.get("username"):
            validated_data["name"] = validated_data["username"]
        instance = AssetUserManager.create(**validated_data)
        return instance


class AssetUserReadSerializer(AssetUserWriteSerializer):
    id = serializers.CharField(read_only=True, source='union_id', label=_("ID"))
    hostname = serializers.CharField(read_only=True, label=_("Hostname"))
    ip = serializers.CharField(read_only=True, label=_("IP"))
    asset = serializers.CharField(source='asset_id', label=_('Asset'))
    backend = serializers.CharField(read_only=True, label=_("Backend"))
    backend_display = serializers.CharField(read_only=True, label=_("Source"))

    class Meta(AssetUserWriteSerializer.Meta):
        read_only_fields = (
            'date_created', 'date_updated',
            'created_by', 'version',
        )
        fields_mini = ['id', 'name', 'username']
        fields_write_only = ['password', 'private_key', "public_key"]
        fields_small = fields_mini + fields_write_only + [
            'backend', 'backend_display', 'version',
            'date_created', "date_updated",
            'comment'
        ]
        fields_fk = ['asset', 'hostname', 'ip']
        fields = fields_small + fields_fk
        extra_kwargs = {
            'name': {'required': False},
            'username': {'required': True},
            'password': {'write_only': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }


class AssetUserAuthInfoSerializer(AssetUserReadSerializer):
    password = serializers.CharField(
        max_length=256, allow_blank=True, allow_null=True,
        required=False, label=_('Password')
    )
    public_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True,
        required=False, label=_('Public key')
    )
    private_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True,
        required=False, label=_('Private key')
    )


class AssetUserPushSerializer(serializers.Serializer):
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects, label=_("Asset"))
    username = serializers.CharField(max_length=1024)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
