# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.const import SecretType
from common.drf.fields import EncryptedField, LabeledChoiceField
from .utils import validate_password_for_ansible, validate_ssh_key


class AuthValidateMixin(serializers.Serializer):
    secret_type = LabeledChoiceField(
        choices=SecretType.choices, required=True, label=_('Secret type')
    )
    secret = EncryptedField(
        label=_('Secret'), required=False, max_length=40960, allow_blank=True,
        allow_null=True, write_only=True,
    )
    passphrase = serializers.CharField(
        allow_blank=True, allow_null=True, required=False, max_length=512,
        write_only=True, label=_('Key password')
    )

    @property
    def initial_secret_type(self):
        secret_type = self.initial_data.get('secret_type')
        return secret_type

    def validate_secret(self, secret):
        if not secret:
            return ''
        secret_type = self.initial_secret_type
        if secret_type == SecretType.PASSWORD:
            validate_password_for_ansible(secret)
            return secret
        elif secret_type == SecretType.SSH_KEY:
            passphrase = self.initial_data.get('passphrase')
            passphrase = passphrase if passphrase else None
            return validate_ssh_key(secret, passphrase)
        else:
            return secret

    @staticmethod
    def clean_auth_fields(validated_data):
        for field in ('secret',):
            value = validated_data.get(field)
            if value is None:
                validated_data.pop(field, None)
        validated_data.pop('passphrase', None)

    def create(self, validated_data):
        self.clean_auth_fields(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self.clean_auth_fields(validated_data)
        return super().update(instance, validated_data)
