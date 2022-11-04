# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import EncryptedField

__all__ = [
    'MFAChallengeSerializer', 'MFASelectTypeSerializer',
    'PasswordVerifySerializer', 'ResetPasswordCodeSerializer',
]


class ResetPasswordCodeSerializer(serializers.Serializer):
    form_type = serializers.CharField(default='email')
    username = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)

    def create(self, attrs):
        error = []
        form_type = attrs.get('form_type', 'email')
        username = attrs.get('username')
        if not username:
            error.append(_('The {} cannot be empty').format(_('Username')))
        if form_type == 'phone':
            phone = attrs.get('phone')
            if not phone:
                error.append(_('The {} cannot be empty').format(_('Phone')))
        else:
            email = attrs.get('email')
            if not email:
                error.append(_('The {} cannot be empty').format(_('Email')))

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
