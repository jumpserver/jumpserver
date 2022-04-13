# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from users.models import User
from assets.models import Asset, SystemUser, Gateway, Domain, CommandFilterRule
from applications.models import Application
from assets.serializers import ProtocolsField
from perms.serializers.base import ActionsField

__all__ = [
    'ConnectionTokenSerializer', 'ConnectionTokenApplicationSerializer',
    'ConnectionTokenUserSerializer', 'ConnectionTokenFilterRuleSerializer',
    'ConnectionTokenAssetSerializer', 'ConnectionTokenSystemUserSerializer',
    'ConnectionTokenDomainSerializer', 'ConnectionTokenRemoteAppSerializer',
    'ConnectionTokenGatewaySerializer', 'ConnectionTokenSecretSerializer'
]


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
    protocols = ProtocolsField(label='Protocols', read_only=True)

    class Meta:
        model = Asset
        fields = ['id', 'hostname', 'ip', 'protocols', 'org_id']


class ConnectionTokenSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = ['id', 'name', 'username', 'password', 'private_key', 'protocol', 'ad_domain', 'org_id']


class ConnectionTokenGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gateway
        fields = ['id', 'ip', 'port', 'username', 'password', 'private_key']


class ConnectionTokenRemoteAppSerializer(serializers.Serializer):
    program = serializers.CharField()
    working_directory = serializers.CharField()
    parameters = serializers.CharField()


class ConnectionTokenApplicationSerializer(serializers.ModelSerializer):
    attrs = serializers.JSONField(read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'name', 'category', 'type', 'attrs', 'org_id']


class ConnectionTokenDomainSerializer(serializers.ModelSerializer):
    gateways = ConnectionTokenGatewaySerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = ['id', 'name', 'gateways']


class ConnectionTokenFilterRuleSerializer(serializers.ModelSerializer):

    class Meta:
        model = CommandFilterRule
        fields = [
            'id', 'type', 'content', 'ignore_case', 'pattern',
            'priority', 'action',
            'date_created',
        ]


class ConnectionTokenSecretSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    secret = serializers.CharField(read_only=True)
    type = serializers.ChoiceField(choices=[('application', 'Application'), ('asset', 'Asset')])
    user = ConnectionTokenUserSerializer(read_only=True)
    asset = ConnectionTokenAssetSerializer(read_only=True)
    remote_app = ConnectionTokenRemoteAppSerializer(read_only=True)
    application = ConnectionTokenApplicationSerializer(read_only=True)
    system_user = ConnectionTokenSystemUserSerializer(read_only=True)
    cmd_filter_rules = ConnectionTokenFilterRuleSerializer(many=True)
    domain = ConnectionTokenDomainSerializer(read_only=True)
    gateway = ConnectionTokenGatewaySerializer(read_only=True)
    actions = ActionsField()
    expired_at = serializers.IntegerField()
