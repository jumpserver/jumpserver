# -*- coding: utf-8 -*-
#
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from authentication.password_reset import validate_target
from common.serializers.fields import EncryptedField

__all__ = [
    'MFAChallengeSerializer', 'MFASelectTypeSerializer',
    'PasswordVerifySerializer', 'ResetPasswordCodeSerializer',
]


class ResetPasswordCodeSerializer(serializers.Serializer):
    form_type = serializers.ChoiceField(
        choices=[('sms', _('SMS')), ('email', _('Email'))], default='email'
    )
    email = serializers.CharField(required=False, allow_blank=True, max_length=254)
    sms = serializers.CharField(required=False, allow_blank=True, max_length=32)

    def validate(self, attrs):
        form_type = attrs['form_type']
        target = attrs.get(form_type, '')
        try:
            validate_target(form_type, target)
        except ValidationError as exc:
            raise serializers.ValidationError({'error': exc.messages[0]})
        return attrs


class PasswordVerifySerializer(serializers.Serializer):
    username = serializers.CharField(required=False, allow_blank=True, allow_null=True)
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
