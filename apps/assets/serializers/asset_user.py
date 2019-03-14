# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework import serializers

from ..models import AuthBook
from ..backends.multi import AssetUserManager

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
        read_only_fields = (
            'date_created', 'date_updated', 'created_by',
            'is_latest', 'version', 'connectivity',
        )
        fields = '__all__'
        extra_kwargs = {
            'username': {'required': True}
        }

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields = [f for f in fields if not f.startswith('_') and f != 'id']
        fields.extend(['connectivity'])
        return fields

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
        fields = ['password', 'private_key', 'public_key']
