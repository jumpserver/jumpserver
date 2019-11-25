# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.utils import get_object_or_none
from users.models import User
from users.serializers import UserProfileSerializer
from .models import AccessKey, LoginConfirmSetting


__all__ = [
    'AccessKeySerializer', 'OtpVerifySerializer', 'BearerTokenSerializer',
    'MFAChallengeSerializer', 'LoginConfirmSettingSerializer',
]


class AccessKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessKey
        fields = ['id', 'secret', 'is_active', 'date_created']
        read_only_fields = ['id', 'secret', 'date_created']


class OtpVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)


class BearerTokenSerializer(serializers.Serializer):
    username = serializers.CharField(allow_null=True, required=False, write_only=True)
    password = serializers.CharField(write_only=True, allow_null=True,
                                     required=False, allow_blank=True)
    public_key = serializers.CharField(write_only=True, allow_null=True,
                                       allow_blank=True, required=False)
    token = serializers.CharField(read_only=True)
    keyword = serializers.SerializerMethodField()
    date_expired = serializers.DateTimeField(read_only=True)
    user = UserProfileSerializer(read_only=True)

    @staticmethod
    def get_keyword(obj):
        return 'Bearer'

    def create(self, validated_data):
        request = self.context.get('request')
        if request.user and not request.user.is_anonymous:
            user = request.user
        else:
            user_id = request.session.get('user_id')
            user = get_object_or_none(User, pk=user_id)
            if not user:
                raise serializers.ValidationError(
                    "user id {} not exist".format(user_id)
                )
        token, date_expired = user.create_bearer_token(request)
        instance = {
            "token": token,
            "date_expired": date_expired,
            "user": user
        }
        return instance


class MFAChallengeSerializer(serializers.Serializer):
    type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    code = serializers.CharField(write_only=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class LoginConfirmSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginConfirmSetting
        fields = ['id', 'user', 'reviewers', 'date_created', 'date_updated']
        read_only_fields = ['date_created', 'date_updated']
