# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework import serializers

from ..models import AuthBook, Asset
from ..backends import AssetUserManager

__all__ = [
    'AssetUserSerializer', 'AssetUserAuthInfoSerializer',
    'AssetUserExportSerializer',
]


class BasicAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['hostname', 'ip']


class AssetUserSerializer(serializers.ModelSerializer):
    hostname = serializers.CharField(read_only=True, label=_("Hostname"))
    ip = serializers.CharField(read_only=True, label=_("IP"))
    connectivity = serializers.CharField(read_only=True, label=_("Connectivity"))

    password = serializers.CharField(
        max_length=256, allow_blank=True, allow_null=True, write_only=True,
        required=False, label=_('Password')
    )
    public_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True, write_only=True,
        required=False, label=_('Public key')
    )
    private_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True, write_only=True,
        required=False, label=_('Private key')
    )
    backend = serializers.CharField(read_only=True, label=_("Backend"))

    class Meta:
        model = AuthBook
        read_only_fields = (
            'date_created', 'date_updated', 'created_by',
            'is_latest', 'version', 'connectivity',
        )
        fields = [
            "id", "hostname", "ip", "username", "password", "asset", "version",
            "is_latest", "connectivity", "backend", "org_id", "name",
            "date_created", "date_updated", "private_key", "public_key",
        ]
        extra_kwargs = {
            'username': {'required': True},
            'name': {'write_only': True},
        }

    def create(self, validated_data):
        kwargs = {
            'name': validated_data.get('name'),
            'username': validated_data.get('username'),
            'asset': validated_data.get('asset'),
            'comment': validated_data.get('comment', ''),
            'org_id': validated_data.get('org_id', ''),
            'password': validated_data.get('password'),
            'public_key': validated_data.get('public_key'),
            'private_key': validated_data.get('private_key')
        }
        instance = AssetUserManager.create(**kwargs)
        return instance


class AssetUserExportSerializer(AssetUserSerializer):
    password = serializers.CharField(
        max_length=256, allow_blank=True, allow_null=True,
        required=False, help_text=_('Password')
    )
    public_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True,
        required=False, help_text=_('Public key')
    )
    private_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True,
        required=False, help_text=_('Private key')
    )


class AssetUserAuthInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthBook
        fields = ['password', 'private_key', 'public_key']
