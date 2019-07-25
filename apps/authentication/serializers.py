# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from users.models import User
from .models import AccessKey


__all__ = [
    'AccessKeySerializer', 'OtpVerifySerializer', 'BearerTokenSerializer',
]


class AccessKeySerializer(serializers.ModelSerializer):

    class Meta:
        model = AccessKey
        fields = ['id', 'secret']
        read_only_fields = ['id', 'secret']


class OtpVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class BearerTokenSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(allow_blank=True, write_only=True)
    public_key = serializers.CharField(allow_blank=True, write_only=True)
    token = serializers.CharField(read_only=True)
    keyword = serializers.SerializerMethodField()

    @staticmethod
    def get_keyword(obj):
        return 'Bearer'

    def create(self, validated_data):
        username = validated_data["username"]
        request = self.context.get("request")
        user = User.objects.get(username=username)
        instance = {
            "username": validated_data.get(username),
            "token": user.create_bearer_token(request),
        }
        return instance

    def update(self, instance, validated_data):
        pass


