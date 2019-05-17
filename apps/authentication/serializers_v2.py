# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from .models import AccessKey


__all__ = ['UserTokenSerializer', 'OTPAuthSerializer', 'MFAAuthSerializer']


class UserTokenSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    password = serializers.CharField(required=False)
    public_key = serializers.CharField(required=False)


class OTPAuthSerializer(serializers.Serializer):
    pre_token = serializers.CharField(required=False)
    code = serializers.CharField(required=True, max_length=6, min_length=6)


class MFAAuthSerializer(serializers.Serializer):
    choices = serializers.ListField()
    last_time = serializers.IntegerField()
