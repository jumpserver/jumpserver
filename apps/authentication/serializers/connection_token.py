from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from authentication.models import ConnectionToken
from common.utils import pretty_string
from common.utils.random import random_string
from assets.models import Asset, SystemUser, Gateway, Domain, CommandFilterRule
from users.models import User
from applications.models import Application
from assets.serializers import ProtocolsField
from perms.serializers.base import ActionsField


__all__ = [
    'ConnectionTokenSerializer', 'ConnectionTokenSecretSerializer',
    'SuperConnectionTokenSerializer', 'ConnectionTokenDisplaySerializer'
]


class ConnectionTokenSerializer(OrgResourceModelSerializerMixin):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_("Type display"))
    is_valid = serializers.BooleanField(read_only=True, label=_('Validity'))
    expire_time = serializers.IntegerField(read_only=True, label=_('Expired time'))

    class Meta:
        model = ConnectionToken
        fields_mini = ['id', 'type']
        fields_small = fields_mini + [
            'secret', 'date_expired', 'date_created', 'date_updated',
            'created_by', 'updated_by', 'org_id', 'org_name',
        ]
        fields_fk = [
            'user', 'system_user', 'asset', 'application',
        ]
        read_only_fields = [
            # 普通 Token 不支持指定 user
            'user', 'is_valid', 'expire_time',
            'type_display', 'user_display', 'system_user_display',
            'asset_display', 'application_display',
        ]
        fields = fields_small + fields_fk + read_only_fields

    def validate(self, attrs):
        fields_attrs = self.construct_internal_fields_attrs(attrs)
        attrs.update(fields_attrs)
        return attrs

    @property
    def request_user(self):
        request = self.context.get('request')
        if request:
            return request.user

    def get_user(self, attrs):
        return self.request_user

    def construct_internal_fields_attrs(self, attrs):
        user = self.get_user(attrs)
        system_user = attrs.get('system_user') or ''
        asset = attrs.get('asset') or ''
        application = attrs.get('application') or ''
        secret = attrs.get('secret') or random_string(16)
        date_expired = attrs.get('date_expired') or ConnectionToken.get_default_date_expired()

        if isinstance(asset, Asset):
            tp = ConnectionToken.Type.asset
            org_id = asset.org_id
        elif isinstance(application, Application):
            tp = ConnectionToken.Type.application
            org_id = application.org_id
        else:
            raise serializers.ValidationError(_('Asset or application required'))

        return {
            'type': tp,
            'user': user,
            'secret': secret,
            'date_expired': date_expired,
            'user_display': pretty_string(str(user), max_length=128),
            'system_user_display': pretty_string(str(system_user), max_length=128),
            'asset_display': pretty_string(str(asset), max_length=128),
            'application_display': pretty_string(str(application), max_length=128),
            'org_id': org_id,
        }


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
        return attrs.get('user') or self.request_user


#
# Connection Token Secret
#


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
        fields = [
            'id', 'name', 'username', 'password', 'private_key',
            'protocol', 'ad_domain', 'org_id'
        ]


class ConnectionTokenGatewaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gateway
        fields = ['id', 'ip', 'port', 'username', 'password', 'private_key']


class ConnectionTokenRemoteAppSerializer(serializers.Serializer):
    program = serializers.CharField(allow_null=True, allow_blank=True)
    working_directory = serializers.CharField(allow_null=True, allow_blank=True)
    parameters = serializers.CharField(allow_null=True, allow_blank=True)


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


class ConnectionTokenCmdFilterRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandFilterRule
        fields = [
            'id', 'type', 'content', 'ignore_case', 'pattern',
            'priority', 'action', 'date_created',
        ]


class ConnectionTokenSecretSerializer(OrgResourceModelSerializerMixin):
    user = ConnectionTokenUserSerializer(read_only=True)
    asset = ConnectionTokenAssetSerializer(read_only=True, source='asset_or_remote_app_asset')
    application = ConnectionTokenApplicationSerializer(read_only=True)
    remote_app = ConnectionTokenRemoteAppSerializer(read_only=True)
    system_user = ConnectionTokenSystemUserSerializer(read_only=True)
    gateway = ConnectionTokenGatewaySerializer(read_only=True)
    domain = ConnectionTokenDomainSerializer(read_only=True)
    cmd_filter_rules = ConnectionTokenCmdFilterRuleSerializer(many=True)
    actions = ActionsField()
    expired_at = serializers.IntegerField()

    class Meta:
        model = ConnectionToken
        fields = [
            'id', 'secret', 'type', 'user', 'asset', 'application', 'system_user',
            'remote_app', 'cmd_filter_rules', 'domain', 'gateway', 'actions', 'expired_at',
        ]
