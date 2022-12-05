from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from users.models import User
from assets.models import Asset, Account, Platform
from assets.serializers import PlatformSerializer, AssetProtocolsSerializer
from perms.serializers.permission import ActionChoicesField
from acls.models import CommandGroup, CommandFilterACL
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from common.drf.fields import ObjectRelatedField

from ..models import ConnectionToken

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
            'connect_method', 'protocol',
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
        fields = [
            'id', 'name', 'address', 'protocols', 'category', 'type', 'org_id', 'specific'
        ]


class SimpleAccountSerializer(serializers.ModelSerializer):
    """ Account """

    class Meta:
        model = Account
        fields = ['name', 'username', 'secret_type', 'secret']


class ConnectionTokenAccountSerializer(serializers.ModelSerializer):
    """ Account """
    su_from = SimpleAccountSerializer(required=False, label=_('Su from'))

    class Meta:
        model = Account
        fields = [
            'name', 'username', 'secret_type', 'secret', 'su_from',
        ]


class ConnectionTokenGatewaySerializer(serializers.ModelSerializer):
    """ Gateway """

    class Meta:
        model = Asset
        fields = [
            'id', 'address', 'port',
            # 'username', 'password', 'private_key'
        ]


class ConnectionTokenACLSerializer(serializers.ModelSerializer):
    command_groups = ObjectRelatedField(
        many=True, required=False, queryset=CommandGroup.objects,
        attrs=('id', 'name', 'type', 'content', 'ignore_case', 'pattern'),
        label=_('Command group')
    )
    reviewers = ObjectRelatedField(
        many=True, queryset=User.objects, label=_("Reviewers"), required=False
    )

    class Meta:
        model = CommandFilterACL
        fields = [
            'id', 'name', 'command_groups', 'action', 'reviewers', 'priority', 'is_active'
        ]


class ConnectionTokenPlatform(PlatformSerializer):
    class Meta(PlatformSerializer.Meta):
        model = Platform

    def get_field_names(self, declared_fields, info):
        names = super().get_field_names(declared_fields, info)
        names = [n for n in names if n not in ['automation']]
        return names


class ConnectionTokenSecretSerializer(OrgResourceModelSerializerMixin):
    user = ConnectionTokenUserSerializer(read_only=True)
    asset = ConnectionTokenAssetSerializer(read_only=True)
    account = ConnectionTokenAccountSerializer(read_only=True)
    gateway = ConnectionTokenGatewaySerializer(read_only=True)
    platform = ConnectionTokenPlatform(read_only=True)
    command_filter_acls = ConnectionTokenACLSerializer(read_only=True, many=True)
    actions = ActionChoicesField()
    expire_at = serializers.IntegerField()
    expire_now = serializers.BooleanField(label=_('Expired now'), write_only=True, default=True)

    class Meta:
        model = ConnectionToken
        fields = [
            'id', 'value', 'user', 'asset', 'account', 'platform',
            'command_filter_acls',
            'protocol', 'gateway', 'actions', 'expire_at', 'expire_now',
        ]
        extra_kwargs = {
            'value': {'read_only': True},
        }
