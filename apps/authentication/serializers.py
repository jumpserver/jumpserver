# -*- coding: utf-8 -*-
#
from django.core.cache import cache
from rest_framework import serializers

from users.models import User
from .models import AccessKey


__all__ = [
    'AccessKeySerializer', 'OtpVerifySerializer', 'BearerTokenSerializer',
    'MFAChallengeSerializer',
]


class AccessKeySerializer(serializers.ModelSerializer):

    class Meta:
        model = AccessKey
        fields = ['id', 'secret', 'is_active', 'date_created']
        read_only_fields = ['id', 'secret', 'date_created']


class OtpVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class BearerTokenMixin(serializers.Serializer):
    token = serializers.CharField(read_only=True)
    keyword = serializers.SerializerMethodField()
    date_expired = serializers.DateTimeField(read_only=True)

    @staticmethod
    def get_keyword(obj):
        return 'Bearer'

    def create_response(self, username):
        request = self.context.get("request")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("username %s not exist" % username)
        token, date_expired = user.create_bearer_token(request)
        instance = {
            "username": username,
            "token": token,
            "date_expired": date_expired,
        }
        return instance

    def update(self, instance, validated_data):
        pass


class BearerTokenSerializer(BearerTokenMixin, serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, allow_null=True,
                                     required=False)
    public_key = serializers.CharField(write_only=True, allow_null=True,
                                       required=False)

    def create(self, validated_data):
        username = validated_data.get("username")
        return self.create_response(username)


class MFAChallengeSerializer(BearerTokenMixin, serializers.Serializer):
    req = serializers.CharField(write_only=True)
    auth_type = serializers.CharField(write_only=True)
    code = serializers.CharField(write_only=True)

    def validate_req(self, attr):
        username = cache.get(attr)
        if not username:
            raise serializers.ValidationError("Not valid, may be expired")
        self.context["username"] = username

    def validate_code(self, code):
        username = self.context["username"]
        user = User.objects.get(username=username)
        ok = user.check_otp(code)
        if not ok:
            msg = "Otp code not valid, may be expired"
            raise serializers.ValidationError(msg)

    def create(self, validated_data):
        username = self.context["username"]
        return self.create_response(username)

