# -*- coding: utf-8 -*-
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretType
from accounts.models import BaseAccount
from accounts.utils import validate_password_for_ansible, validate_ssh_key
from common.serializers import ResourceLabelsMixin
from common.serializers.fields import EncryptedField, LabeledChoiceField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

__all__ = ['AuthValidateMixin', 'BaseAccountSerializer']


class AuthValidateMixin(serializers.Serializer):
    secret_type = LabeledChoiceField(
        choices=SecretType.choices, label=_('Secret type'), default='password'
    )
    secret = EncryptedField(
        label=_('Secret'), required=False, max_length=40960, allow_blank=True,
        allow_null=True, write_only=True,
    )
    passphrase = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, max_length=512,
        write_only=True, label=_('Key password')
    )

    @staticmethod
    def handle_secret(secret, secret_type, passphrase=None):
        if not secret:
            return ''
        if secret_type == SecretType.PASSWORD:
            validate_password_for_ansible(secret)
            return secret
        elif secret_type == SecretType.SSH_KEY:
            passphrase = passphrase if passphrase else None
            secret = validate_ssh_key(secret, passphrase)
            return secret
        else:
            return secret

    def clean_auth_fields(self, validated_data):
        secret_type = validated_data.get('secret_type')
        passphrase = validated_data.get('passphrase')
        secret = validated_data.pop('secret', None)
        validated_data['secret'] = self.handle_secret(
            secret, secret_type, passphrase
        )
        for field in ('secret',):
            value = validated_data.get(field)
            if not value:
                validated_data.pop(field, None)
        validated_data.pop('passphrase', None)

    def create(self, validated_data):
        self.clean_auth_fields(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.clean_auth_fields(validated_data)
        return super().update(instance, validated_data)


class BaseAccountSerializer(AuthValidateMixin, ResourceLabelsMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = BaseAccount
        fields_mini = ['id', 'name', 'username']
        fields_small = fields_mini + [
            'secret_type', 'secret', 'passphrase',
            'privileged', 'is_active', 'spec_info',
        ]
        fields_other = ['created_by', 'date_created', 'date_updated', 'comment']
        fields = fields_small + fields_other + ['labels']
        read_only_fields = [
            'spec_info', 'date_verified', 'created_by', 'date_created',
        ]
        extra_kwargs = {
            'spec_info': {'label': _('Spec info')},
            'username': {'help_text': _(
                "Tip: If no username is required for authentication, fill in `null`, "
                "If AD account, like `username@domain`"
            )},
        }
