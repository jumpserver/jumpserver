# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import AuthBook, Asset
from ..backends import AssetUserManager
from .base import ConnectivitySerializer, AuthSerializerMixin


__all__ = [
    'AssetUserSerializer', 'AssetUserAuthInfoSerializer',
    'AssetUserExportSerializer', 'AssetUserPushSerializer',
]


class BasicAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['hostname', 'ip']


class AssetUserSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    hostname = serializers.CharField(read_only=True, label=_("Hostname"))
    ip = serializers.CharField(read_only=True, label=_("IP"))
    connectivity = ConnectivitySerializer(read_only=True, label=_("Connectivity"))

    backend = serializers.CharField(read_only=True, label=_("Backend"))

    class Meta:
        model = AuthBook
        list_serializer_class = AdaptedBulkListSerializer
        read_only_fields = (
            'date_created', 'date_updated', 'created_by',
            'is_latest', 'version', 'connectivity',
        )
        fields = [
            "id", "hostname", "ip", "username", "password", "asset", "version",
            "is_latest", "connectivity", "backend",
            "date_created", "date_updated", "private_key", "public_key",
        ]
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
        instance.set_to_latest()
        return instance


class AssetUserExportSerializer(AssetUserSerializer):
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


class AssetUserAuthInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthBook
        fields = ['password', 'private_key', 'public_key']


class AssetUserPushSerializer(serializers.Serializer):
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects, label=_("Asset"))
    username = serializers.CharField(max_length=1024)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
