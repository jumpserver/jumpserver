# -*- coding: utf-8 -*-
#
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from common.utils import get_object_or_none, random_string
from users.models import User
from users.serializers import UserProfileSerializer
from ..models import AccessKey, TempToken

__all__ = [
    'AccessKeySerializer', 'BearerTokenSerializer',
    'SSOTokenSerializer', 'TempTokenSerializer',
    'AccessKeyCreateSerializer'
]


class AccessKeySerializer(serializers.ModelSerializer):
    ip_group = serializers.ListField(
        default=['*'], label=_('Access IP'), help_text=ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator])
    )

    class Meta:
        model = AccessKey
        fields = ['id', 'is_active', 'date_created', 'date_last_used'] + ['ip_group']
        read_only_fields = ['id', 'date_created', 'date_last_used']


class AccessKeyCreateSerializer(AccessKeySerializer):
    class Meta(AccessKeySerializer.Meta):
        fields = AccessKeySerializer.Meta.fields + ['secret']


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

    @staticmethod
    def update_last_login(user):
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
    is_valid = serializers.BooleanField(label=_("Is valid"), read_only=True)

    class Meta:
        model = TempToken
        fields = [
            'id', 'username', 'secret', 'verified', 'is_valid',
            'date_created', 'date_updated', 'date_verified',
            'date_expired',
        ]
        read_only_fields = fields

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user:
            raise PermissionError()

        secret = random_string(36)
        username = request.user.username
        kwargs = {
            'username': username, 'secret': secret,
            'date_expired': timezone.now() + timezone.timedelta(seconds=5 * 60),
        }
        token = TempToken(**kwargs)
        token.save()
        return token
