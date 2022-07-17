# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.drf.fields import EncryptedField

__all__ = [
    'MFAChallengeSerializer', 'MFASelectTypeSerializer',
    'PasswordVerifySerializer',
]


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
