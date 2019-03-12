# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework import serializers

from ..models import AuthBook
from ..asset_user_manager import AssetUserManager

__all__ = [
    'AssetUserSerializer', 'AssetUserAuthInfoSerializer',
]


class AssetUserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        max_length=256, allow_blank=True, allow_null=True, write_only=True,
        required=False, help_text=_('Password')
    )
    public_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True, write_only=True,
        required=False, help_text=_('Public key')
    )
    private_key = serializers.CharField(
        max_length=4096, allow_blank=True, allow_null=True, write_only=True,
        required=False, help_text=_('Private key')
    )

    class Meta:
        model = AuthBook
        exclude = ('_password', '_public_key', '_private_key')
        read_only_fields = (
            'id', 'date_created', 'date_updated', 'created_by', 'is_latest',
            'version'
        )
        extra_kwargs = {
            'username': {'required': True}
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


class AssetUserAuthInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthBook
        fields = [
            'id', 'name', 'username', 'asset', 'comment', 'org_id', 'is_latest',
            'date_created', 'date_updated', 'created_by', 'version',
            'password', 'private_key', 'public_key'
        ]
