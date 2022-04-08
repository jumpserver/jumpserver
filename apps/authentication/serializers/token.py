# -*- coding: utf-8 -*-
#
from django.utils import timezone
from rest_framework import serializers

from common.utils import get_object_or_none, random_string
from users.models import User
from users.serializers import UserProfileSerializer
from ..models import AccessKey, TempToken

__all__ = [
    'AccessKeySerializer',  'BearerTokenSerializer',
    'SSOTokenSerializer', 'TempTokenSerializer',
]


class AccessKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessKey
        fields = ['id', 'secret', 'is_active', 'date_created']
        read_only_fields = ['id', 'secret', 'date_created']


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

    def update_last_login(self, user):
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

    def get_request_user(self):
        request = self.context.get('request')
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            user_id = request.session.get('user_id')
            user = get_object_or_none(User, pk=user_id)
            if not user:
                raise serializers.ValidationError(
                    "user id {} not exist".format(user_id)
                )
        return user

    def create(self, validated_data):
        request = self.context.get('request')
        user = self.get_request_user()

        token, date_expired = user.create_bearer_token(request)
        self.update_last_login(user)

        instance = {
            "token": token,
            "date_expired": date_expired,
            "user": user
        }
        return instance


class SSOTokenSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    login_url = serializers.CharField(read_only=True)
    next = serializers.CharField(write_only=True, allow_blank=True, required=False, allow_null=True)


class TempTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TempToken
        fields = '__all__'
        read_only_fields = [
            'id', 'username', 'secret', 'verified',
            'date_create', 'date_updated',
            'date_verified',
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user:
            raise PermissionError()

        secret = random_string(36)
        username = request.user.username
        token = TempToken(username=username, secret=secret)
        token.save()
        return token
