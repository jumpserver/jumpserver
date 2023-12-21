from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretType
from accounts.models import Account
from acls.models import CommandGroup, CommandFilterACL
from assets.models import Asset, Platform, Gateway, Domain
from assets.serializers.asset import AssetProtocolsSerializer
from assets.serializers.platform import PlatformSerializer
from common.serializers.fields import LabeledChoiceField
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from perms.serializers.permission import ActionChoicesField
from users.models import User
from ..models import ConnectionToken

__all__ = [
    'ConnectionTokenSecretSerializer', 'ConnectTokenAppletOptionSerializer',
    'ConnectTokenVirtualAppOptionSerializer',
]


class _ConnectionTokenUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username', 'email']


class _ConnectionTokenAssetSerializer(serializers.ModelSerializer):
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))
    info = serializers.DictField()

    class Meta:
        model = Asset
        fields = [
            'id', 'name', 'address', 'protocols', 'category',
            'type', 'org_id', 'info', 'secret_info', 'spec_info'
        ]


class _SimpleAccountSerializer(serializers.ModelSerializer):
    secret_type = LabeledChoiceField(choices=SecretType.choices, required=False, label=_('Secret type'))

    class Meta:
        model = Account
        fields = ['name', 'username', 'secret_type', 'secret']


class _ConnectionTokenAccountSerializer(serializers.ModelSerializer):
    su_from = serializers.SerializerMethodField(label=_('Su from'))
    secret_type = LabeledChoiceField(choices=SecretType.choices, required=False, label=_('Secret type'))

    class Meta:
        model = Account
        fields = [
            'id', 'name', 'username', 'secret_type',
            'secret', 'su_from', 'privileged'
        ]

    @staticmethod
    def get_su_from(account):
        if not hasattr(account, 'asset'):
            return {}
        su_enabled = account.asset.platform.su_enabled
        su_from = account.su_from
        if not su_from or not su_enabled:
            return
        return _SimpleAccountSerializer(su_from).data


class _ConnectionTokenGatewaySerializer(serializers.ModelSerializer):
    account = _SimpleAccountSerializer(
        required=False, source='select_account', read_only=True
    )
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))

    class Meta:
        model = Gateway
        fields = [
            'id', 'name', 'address', 'protocols', 'account'
        ]


class _ConnectionTokenCommandFilterACLSerializer(serializers.ModelSerializer):
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
            'id', 'name', 'command_groups', 'action',
            'reviewers', 'priority', 'is_active'
        ]


class _ConnectionTokenPlatformSerializer(PlatformSerializer):
    class Meta(PlatformSerializer.Meta):
        model = Platform

    def get_field_names(self, declared_fields, info):
        names = super().get_field_names(declared_fields, info)
        names = [n for n in names if n not in ['automation']]
        return names


class _ConnectionTokenConnectMethodSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('Name'))
    protocol = serializers.CharField(label=_('Protocol'))
    os = serializers.CharField(label=_('OS'))
    is_builtin = serializers.BooleanField(label=_('Is builtin'))
    is_active = serializers.BooleanField(label=_('Is active'))
    platform = _ConnectionTokenPlatformSerializer(label=_('Platform'))
    action = ActionChoicesField(label=_('Action'))
    options = serializers.JSONField(label=_('Options'))


class _ConnectTokenConnectMethodSerializer(serializers.Serializer):
    label = serializers.CharField(label=_('Label'))
    value = serializers.CharField(label=_('Value'))
    type = serializers.CharField(label=_('Type'))
    component = serializers.CharField(label=_('Component'))


class ConnectionTokenSecretSerializer(OrgResourceModelSerializerMixin):
    user = _ConnectionTokenUserSerializer(read_only=True)
    asset = _ConnectionTokenAssetSerializer(read_only=True)
    account = _ConnectionTokenAccountSerializer(read_only=True, source='account_object')
    gateway = _ConnectionTokenGatewaySerializer(read_only=True)
    platform = _ConnectionTokenPlatformSerializer(read_only=True)
    domain = ObjectRelatedField(queryset=Domain.objects, required=False, label=_('Domain'))
    command_filter_acls = _ConnectionTokenCommandFilterACLSerializer(read_only=True, many=True)
    expire_now = serializers.BooleanField(label=_('Expired now'), write_only=True, default=True)
    connect_method = _ConnectTokenConnectMethodSerializer(read_only=True, source='connect_method_object')
    connect_options = serializers.JSONField(read_only=True)
    actions = ActionChoicesField()
    expire_at = serializers.IntegerField()

    class Meta:
        model = ConnectionToken
        fields = [
            'id', 'value', 'user', 'asset', 'account',
            'platform', 'command_filter_acls', 'protocol',
            'domain', 'gateway', 'actions', 'expire_at',
            'from_ticket', 'expire_now', 'connect_method',
            'connect_options',
        ]
        extra_kwargs = {
            'value': {'read_only': True},
        }


class ConnectTokenAppletOptionSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    applet = ObjectRelatedField(read_only=True)
    host = _ConnectionTokenAssetSerializer(read_only=True)
    account = _ConnectionTokenAccountSerializer(read_only=True)
    gateway = _ConnectionTokenGatewaySerializer(read_only=True)
    remote_app_option = serializers.JSONField(read_only=True)


class ConnectTokenVirtualAppOptionSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('Name'))
    image_name = serializers.CharField(label=_('Image name'))
    image_port = serializers.IntegerField(label=_('Image port'))
    image_protocol = serializers.CharField(label=_('Image protocol'))
