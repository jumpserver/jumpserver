# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.utils import get_object_or_none
from users.models import User
from assets.models import Asset, SystemUser, Gateway
from applications.models import Application
from users.serializers import UserProfileSerializer
from perms.serializers.asset.permission import ActionsField
from .models import AccessKey, LoginConfirmSetting, SSOToken


__all__ = [
    'AccessKeySerializer', 'OtpVerifySerializer', 'BearerTokenSerializer',
    'MFAChallengeSerializer', 'LoginConfirmSettingSerializer', 'SSOTokenSerializer',
    'ConnectionTokenSerializer', 'ConnectionTokenSecretSerializer', 'RDPFileSerializer'
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


class SSOTokenSerializer(serializers.Serializer):
    username = serializers.CharField(write_only=True)
    login_url = serializers.CharField(read_only=True)
    next = serializers.CharField(write_only=True, allow_blank=True, required=False, allow_null=True)


class ConnectionTokenSerializer(serializers.Serializer):
    user = serializers.CharField(max_length=128, required=False, allow_blank=True)
    system_user = serializers.CharField(max_length=128, required=True)
    asset = serializers.CharField(max_length=128, required=False)
    application = serializers.CharField(max_length=128, required=False)

    @staticmethod
    def validate_user(user_id):
        from users.models import User
        user = User.objects.filter(id=user_id).first()
        if user is None:
            raise serializers.ValidationError('user id not exist')
        return user

    @staticmethod
    def validate_system_user(system_user_id):
        from assets.models import SystemUser
        system_user = SystemUser.objects.filter(id=system_user_id).first()
        if system_user is None:
            raise serializers.ValidationError('system_user id not exist')
        return system_user

    @staticmethod
    def validate_asset(asset_id):
        from assets.models import Asset
        asset = Asset.objects.filter(id=asset_id).first()
        if asset is None:
            raise serializers.ValidationError('asset id not exist')
        return asset

    @staticmethod
    def validate_application(app_id):
        from applications.models import Application
        app = Application.objects.filter(id=app_id).first()
        if app is None:
            raise serializers.ValidationError('app id not exist')
        return app

    def validate(self, attrs):
        asset = attrs.get('asset')
        application = attrs.get('application')
        if not asset and not application:
            raise serializers.ValidationError('asset or application required')
        if asset and application:
            raise serializers.ValidationError('asset and application should only one')
        return super().validate(attrs)


class ConnectionTokenUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username', 'email']


class ConnectionTokenAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'hostname', 'ip', 'port', 'org_id']


class ConnectionTokenSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = ['id', 'name', 'username', 'password', 'private_key']


class ConnectionTokenGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gateway
        fields = ['id', 'ip', 'port', 'username', 'password', 'private_key']


class ConnectionTokenRemoteAppSerializer(serializers.Serializer):
    program = serializers.CharField()
    working_directory = serializers.CharField()
    parameters = serializers.CharField()


class ConnectionTokenApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'name', 'category', 'type']


class ConnectionTokenSecretSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[('application', 'Application'), ('asset', 'Asset')])
    user = ConnectionTokenUserSerializer(read_only=True)
    asset = ConnectionTokenAssetSerializer(read_only=True)
    remote_app = ConnectionTokenRemoteAppSerializer(read_only=True)
    application = ConnectionTokenApplicationSerializer(read_only=True)
    system_user = ConnectionTokenSystemUserSerializer(read_only=True)
    gateway = ConnectionTokenGatewaySerializer(read_only=True)
    actions = ActionsField()


class RDPFileSerializer(ConnectionTokenSerializer):
    width = serializers.IntegerField(default=1280)
    height = serializers.IntegerField(default=800)
