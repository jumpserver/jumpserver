# -*- coding: utf-8 -*-
#
from rest_framework import serializers

__all__ = [
    'BaseAccountSerializer',
]


class BaseAccountSerializer(serializers.ModelSerializer):
    class Meta:
        fields_mini = [
            'id', 'privileged', 'username', 'ip', 'asset_name',
            'platform', 'version'
        ]
        fields_write_only = ['password', 'private_key', 'public_key', 'passphrase']
        fields_other = ['date_created', 'date_updated', 'connectivity', 'date_verified', 'comment']
        fields_small = fields_mini + fields_write_only + fields_other
        fields_fk = ['asset']
        fields = fields_small + fields_fk
        ref_name = 'AssetAccountSerializer'
        extra_kwargs = {
            'username': {'required': True},
            'private_key': {'write_only': True},
            'public_key': {'write_only': True},
        }
