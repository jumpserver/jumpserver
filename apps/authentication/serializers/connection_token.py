from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from authentication.models import ConnectionToken
from common.utils import pretty_string
from common.utils.random import random_string
from assets.models import Asset, Gateway, Domain, CommandFilterRule, Account
from users.models import User
from perms.serializers.permission import ActionsField


__all__ = [
    'ConnectionTokenSerializer', 'ConnectionTokenSecretSerializer',
    'SuperConnectionTokenSerializer', 'ConnectionTokenDisplaySerializer'
]


class ConnectionTokenSerializer(OrgResourceModelSerializerMixin):
    is_valid = serializers.BooleanField(read_only=True, label=_('Validity'))
    expire_time = serializers.IntegerField(read_only=True, label=_('Expired time'))

    class Meta:
        model = ConnectionToken
        fields_mini = ['id']
        fields_small = fields_mini + [
            'secret', 'account_username', 'date_expired',
            'date_created', 'date_updated',
            'created_by', 'updated_by', 'org_id', 'org_name',
        ]
        fields_fk = [
            'user', 'asset',
        ]
        read_only_fields = [
            # 普通 Token 不支持指定 user
            'user', 'is_valid', 'expire_time',
            'user_display', 'asset_display',
        ]
        fields = fields_small + fields_fk + read_only_fields

    def get_request_user(self):
        request = self.context.get('request')
        user = request.user if request else None
        return user

    def get_user(self, attrs):
        return self.get_request_user()

    def validate(self, attrs):
        fields_attrs = self.construct_internal_fields_attrs(attrs)
        attrs.update(fields_attrs)
        return attrs

    def construct_internal_fields_attrs(self, attrs):
        asset = attrs.get('asset') or ''
        asset_display = pretty_string(str(asset), max_length=128)
        user = self.get_user(attrs)
        user_display = pretty_string(str(user), max_length=128)
        secret = attrs.get('secret') or random_string(16)
        date_expired = attrs.get('date_expired') or ConnectionToken.get_default_date_expired()
        org_id = asset.org_id
        if not isinstance(asset, Asset):
            error = ''
            raise serializers.ValidationError(error)
        attrs = {
            'user': user,
            'secret': secret,
            'user_display': user_display,
            'asset_display': asset_display,
            'date_expired': date_expired,
            'org_id': org_id,
        }
        return attrs


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
    class Meta:
        model = Asset
        fields = ['id', 'name', 'ip', 'protocols', 'org_id']


class ConnectionTokenAccountSerializer(serializers.ModelSerializer):
    """ Account """
    class Meta:
        model = Account
        fields = [
            'id', 'name', 'username', 'secret_type', 'secret', 'version'
        ]


class ConnectionTokenGatewaySerializer(serializers.ModelSerializer):
    """ Gateway """
    class Meta:
        model = Gateway
        fields = ['id', 'ip', 'port', 'username', 'password', 'private_key']


class ConnectionTokenDomainSerializer(serializers.ModelSerializer):
    """ Domain """
    gateways = ConnectionTokenGatewaySerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = ['id', 'name', 'gateways']


class ConnectionTokenCmdFilterRuleSerializer(serializers.ModelSerializer):
    """ Command filter rule """
    class Meta:
        model = CommandFilterRule
        fields = [
            'id', 'type', 'content', 'ignore_case', 'pattern',
            'priority', 'action', 'date_created',
        ]


class ConnectionTokenSecretSerializer(OrgResourceModelSerializerMixin):
    user = ConnectionTokenUserSerializer(read_only=True)
    asset = ConnectionTokenAssetSerializer(read_only=True)
    account = ConnectionTokenAccountSerializer(read_only=True)
    gateway = ConnectionTokenGatewaySerializer(read_only=True)
    domain = ConnectionTokenDomainSerializer(read_only=True)
    cmd_filter_rules = ConnectionTokenCmdFilterRuleSerializer(many=True)
    actions = ActionsField()
    expired_at = serializers.IntegerField()

    class Meta:
        model = ConnectionToken
        fields = [
            'id', 'secret',
            'user', 'asset', 'account_username', 'account', 'protocol',
            'domain', 'gateway', 'cmd_filter_rules',
            'actions', 'expired_at',
        ]
