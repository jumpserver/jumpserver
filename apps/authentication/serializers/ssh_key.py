# -*- coding: utf-8 -*-
#
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField
from ..models import SSHKey
from common.utils import validate_ssh_public_key

__all__ = ['SSHKeySerializer']


class SSHKeySerializer(serializers.ModelSerializer):
    user = ReadableHiddenField(default=serializers.CurrentUserDefault())
    public_key_comment = serializers.CharField(
        source='get_public_key_comment', required=False, read_only=True, max_length=128
    )
    public_key_hash_md5 = serializers.CharField(
        source='get_public_key_hash_md5', required=False, read_only=True, max_length=128
    )

    class Meta:
        model = SSHKey
        fields_mini = ['name']
        fields_small = fields_mini + [
            'public_key', 'is_active',
        ]
        read_only_fields = [
            'id', 'user', 'public_key_comment', 'public_key_hash_md5',
            'date_last_used', 'date_created', 'date_updated'
        ]
        fields = fields_small + read_only_fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('public_key', None)
        return data

    @staticmethod
    def validate_public_key(value):
        if not validate_ssh_public_key(value):
            raise serializers.ValidationError(_('Not a valid ssh public key'))
        return value
