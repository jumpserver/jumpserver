from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import Asset, CommandFilterRule, Account, Platform
from assets.serializers import PlatformSerializer, AssetProtocolsSerializer
from authentication.models import ConnectionToken
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from perms.serializers.permission import ActionChoicesField
from users.models import User

__all__ = [
    'ConnectionTokenSerializer', 'ConnectionTokenSecretSerializer',
    'SuperConnectionTokenSerializer', 'ConnectionTokenDisplaySerializer'
]


class ConnectionTokenSerializer(OrgResourceModelSerializerMixin):
    expire_time = serializers.IntegerField(read_only=True, label=_('Expired time'))

    class Meta:
        model = ConnectionToken
        fields_mini = ['id', 'value']
        fields_small = fields_mini + [
            'user', 'asset', 'account_name',
            'input_username', 'input_secret',
            'connect_method', 'endpoint_protocol', 'protocol',
            'actions', 'date_expired', 'date_created',
            'date_updated', 'created_by',
            'updated_by', 'org_id', 'org_name',
        ]
        read_only_fields = [
            # 普通 Token 不支持指定 user
            'user', 'expire_time',
            'user_display', 'asset_display',
        ]
        fields = fields_small + read_only_fields
        extra_kwargs = {
            'value': {'read_only': True},
        }

    def get_request_user(self):
        request = self.context.get('request')
        user = request.user if request else None
        return user

    def get_user(self, attrs):
        return self.get_request_user()


class ConnectionTokenDisplaySerializer(ConnectionTokenSerializer):
    class Meta(ConnectionTokenSerializer.Meta):
        extra_kwargs = {
            'secret': {'write_only': True},
        }


#
# SuperConnectionTokenSerializer
#


class SuperConnectionTokenSerializer(ConnectionTokenSerializer):
    class Meta(ConnectionTokenSerializer.Meta):
        read_only_fields = [
            'validity', 'user_display', 'system_user_display',
            'asset_display', 'application_display',
        ]

    def get_user(self, attrs):
        return attrs.get('user') or self.get_request_user()


#
# Connection Token Secret
#


class ConnectionTokenUserSerializer(serializers.ModelSerializer):
    """ User """

    class Meta:
        model = User
        fields = ['id', 'name', 'username', 'email']


class ConnectionTokenAssetSerializer(serializers.ModelSerializer):
    """ Asset """
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))

    class Meta:
        model = Asset
        fields = ['id', 'name', 'address', 'protocols',
                  'org_id', 'specific']


class ConnectionTokenAccountSerializer(serializers.ModelSerializer):
    """ Account """

    class Meta:
        model = Account
        fields = [
            'name', 'username', 'secret_type', 'secret',
        ]


class ConnectionTokenGatewaySerializer(serializers.ModelSerializer):
    """ Gateway """

    class Meta:
        model = Asset
        fields = [
            'id', 'address', 'port', 'username',
            'password', 'private_key'
        ]


class ConnectionTokenCmdFilterRuleSerializer(serializers.ModelSerializer):
    """ Command filter rule """

    class Meta:
        model = CommandFilterRule
        fields = [
            'id', 'type', 'content', 'ignore_case', 'pattern',
            'priority', 'action', 'date_created',
        ]


class ConnectionTokenPlatform(PlatformSerializer):
    class Meta(PlatformSerializer.Meta):
        model = Platform

    def get_field_names(self, declared_fields, info):
        names = super().get_field_names(declared_fields, info)
        names = [n for n in names if n not in ['automation']]
        return names


class ConnectionTokenSecretSerializer(OrgResourceModelSerializerMixin):
    expire_now = serializers.BooleanField(label=_('Expired now'), default=True)
    user = ConnectionTokenUserSerializer(read_only=True)
    asset = ConnectionTokenAssetSerializer(read_only=True)
    platform = ConnectionTokenPlatform(read_only=True)
    account = ConnectionTokenAccountSerializer(read_only=True)
    gateway = ConnectionTokenGatewaySerializer(read_only=True)
    # cmd_filter_rules = ConnectionTokenCmdFilterRuleSerializer(many=True)
    actions = ActionChoicesField()
    expire_at = serializers.IntegerField()

    class Meta:
        model = ConnectionToken
        fields = [
            'id', 'value', 'user', 'asset', 'platform', 'account',
            'protocol', 'gateway', 'actions', 'expire_at', 'expire_now',
        ]
        extra_kwargs = {
            'value': {'read_only': True},
            'expire_now': {'write_only': True},
        }
