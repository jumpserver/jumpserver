# -*- coding: utf-8 -*-
#
from rest_framework import serializers


__all__ = [
    'OtpVerifySerializer', 'MFAChallengeSerializer', 'MFASelectTypeSerializer',
    'PasswordVerifySerializer',
]


class PasswordVerifySerializer(serializers.Serializer):
    password = serializers.CharField()


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


class OtpVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)
