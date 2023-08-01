# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField

__all__ = [
    'MFAChallengeSerializer', 'MFASelectTypeSerializer',
    'PasswordVerifySerializer', 'ResetPasswordCodeSerializer',
]


class ResetPasswordCodeSerializer(serializers.Serializer):
    form_type = serializers.ChoiceField(
        choices=[('sms', _('SMS')), ('email', _('Email'))], default='email'
    )
    email = serializers.CharField(allow_blank=True)
    sms = serializers.CharField(allow_blank=True)

    def create(self, attrs):
        error = []
        validate_backends = {
            'email': _('Email'), 'sms': _('SMS')
        }
        form_type = attrs.get('form_type', 'email')
        validate_backend_input = attrs.get(form_type)
        if not validate_backend_input:
            error.append(_('The {} cannot be empty').format(
                validate_backends.get(validate_backend_input))
            )
        if error:
            raise serializers.ValidationError(error)


class PasswordVerifySerializer(serializers.Serializer):
    password = EncryptedField()


class MFASelectTypeSerializer(serializers.Serializer):
    type = serializers.CharField()
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class MFAChallengeSerializer(serializers.Serializer):
    type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    code = serializers.CharField(write_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass
