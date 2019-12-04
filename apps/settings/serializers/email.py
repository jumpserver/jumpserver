# coding: utf-8
# 

from rest_framework import serializers

__all__ = ['MailTestSerializer']


class MailTestSerializer(serializers.Serializer):
    EMAIL_HOST = serializers.CharField(max_length=1024, required=True)
    EMAIL_PORT = serializers.IntegerField(default=25)
    EMAIL_HOST_USER = serializers.CharField(max_length=1024)
    EMAIL_HOST_PASSWORD = serializers.CharField(required=False, allow_blank=True)
    EMAIL_FROM = serializers.CharField(required=False, allow_blank=True)
    EMAIL_RECIPIENT = serializers.CharField(required=False, allow_blank=True)
    EMAIL_USE_SSL = serializers.BooleanField(default=False)
    EMAIL_USE_TLS = serializers.BooleanField(default=False)
