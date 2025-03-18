# -*- coding: utf-8 -*-
#
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField, LabeledChoiceField
from common.utils import validate_ssh_public_key
from users.exceptions import CreateSSHKeyExceedLimit
from ..models import SSHKey

__all__ = ['SSHKeySerializer', 'GenerateKeyType']


class GenerateKeyType(TextChoices):
    auto = 'auto', _('Automatically Generate Key Pair')
    # 目前只支持sftp方式
    load = 'load', _('Import Existing Key Pair')


class SSHKeySerializer(serializers.ModelSerializer):
    user = ReadableHiddenField(default=serializers.CurrentUserDefault())
    is_active = serializers.BooleanField(default=True, label=_('Active'))
    public_key_comment = serializers.CharField(
        source='get_public_key_comment', required=False, read_only=True, max_length=128
    )
    public_key_hash_md5 = serializers.CharField(
        source='get_public_key_hash_md5', required=False, read_only=True, max_length=128
    )
    generate_key_type = LabeledChoiceField(
        choices=GenerateKeyType.choices, label=_('Create Type'), default=GenerateKeyType.auto.value, required=False,
        help_text=_(
            'Please download the private key after creation. Each private key can only be downloaded once'
        )
    )

    class Meta:
        model = SSHKey
        fields_mini = ['name']
        fields_small = fields_mini + [
            'public_key', 'is_active', 'comment'
        ]
        read_only_fields = [
            'id', 'user', 'public_key_comment', 'public_key_hash_md5',
            'date_last_used', 'date_created', 'date_updated', 'generate_key_type',
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

    def create(self, validated_data):
        if not self.context["request"].user.can_create_ssh_key():
            raise CreateSSHKeyExceedLimit()
        validated_data.pop('generate_key_type', None)
        return super().create(validated_data)
