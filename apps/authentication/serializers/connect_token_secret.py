from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretType
from accounts.models import Account
from acls.const import ActionChoices as ACLActionChoices
from acls.models import CommandGroup, CommandFilterACL, DataMaskingRule
from assets.models import Asset, Platform, Gateway, Zone
from assets.serializers.asset import AssetProtocolsSerializer
from assets.serializers.platform import PlatformSerializer
from common.serializers.fields import LabeledChoiceField
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from perms.const import ActionChoices as PermActionChoices
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
    username = serializers.CharField(label=_('Username'), source='full_username', read_only=True)

    class Meta:
        model = Account
        fields = ['name', 'username', 'secret_type', 'secret']


class _ConnectionTokenAccountSerializer(serializers.ModelSerializer):
    su_from = serializers.SerializerMethodField(label=_('Su from'))
    secret_type = LabeledChoiceField(choices=SecretType.choices, required=False, label=_('Secret type'))
    username = serializers.CharField(label=_('Username'), source='full_username', read_only=True)

    class Meta:
        model = Account
        fields = [
            'id', 'name', 'username', 'secret_type',
            'secret', 'su_from', 'privileged'
        ]

    @staticmethod
    def get_su_from(account) -> dict:
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


class _ConnectionTokenDataMaskingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataMaskingRule
        fields = ['id', 'name', 'fields_pattern',
                  'masking_method', 'mask_pattern',
                  'is_active', 'priority']


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
        fields = [field for field in PlatformSerializer.Meta.fields
                  if field not in PlatformSerializer.Meta.fields_m2m]

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
    zone = ObjectRelatedField(queryset=Zone.objects, required=False, label=_('Domain'))
    command_filter_acls = _ConnectionTokenCommandFilterACLSerializer(read_only=True, many=True)
    clipboard_policy = serializers.SerializerMethodField()
    data_masking_rules = _ConnectionTokenDataMaskingRuleSerializer(read_only=True, many=True)
    expire_now = serializers.BooleanField(label=_('Expired now'), write_only=True, default=True)
    connect_method = _ConnectTokenConnectMethodSerializer(read_only=True, source='connect_method_object')
    connect_options = serializers.JSONField(read_only=True)
    actions = ActionChoicesField()
    expire_at = serializers.IntegerField()

    class Meta:
        model = ConnectionToken
        fields = [
            'id', 'value', 'user', 'asset', 'account',
            'platform', 'command_filter_acls', 'clipboard_policy', 'data_masking_rules', 'protocol',
            'zone', 'gateway', 'actions', 'expire_at',
            'from_ticket', 'expire_now', 'connect_method',
            'connect_options', 'face_monitor_token'
        ]
        extra_kwargs = {
            'face_monitor_token': {'read_only': True},
            'value': {'read_only': True},
        }

    @staticmethod
    def _get_clipboard_acl_for_operation(token, operation):
        return next(
            (acl for acl in token.clipboard_acls if acl.matches_operation(operation)),
            None,
        )

    def get_clipboard_policy(self, token):
        operation_map = {
            'copy': {
                'operation': PermActionChoices.copy,
                'text_limit_field': 'copy_text_limit',
                'file_size_limit_field': 'download_file_size_limit',
            },
            'paste': {
                'operation': PermActionChoices.paste,
                'text_limit_field': 'paste_text_limit',
                'file_size_limit_field': 'upload_file_size_limit',
            },
        }
        policy = {}
        for name, config in operation_map.items():
            operation = config['operation']
            acl = self._get_clipboard_acl_for_operation(token, operation)
            perm_allowed = PermActionChoices.contains(token.actions, operation)
            acl_allowed = acl is None or acl.action == ACLActionChoices.accept
            enabled = perm_allowed and acl_allowed
            policy[name] = {
                'enabled': enabled,
                'action': ACLActionChoices.accept.value if enabled else ACLActionChoices.reject.value,
                'perm_allowed': perm_allowed,
                'acl_action': acl.action if acl else None,
                'text_limit': getattr(acl, config['text_limit_field'], 0) if acl else 0,
                'file_size_limit': getattr(acl, config['file_size_limit_field'], 0) if acl else 0,
            }
        return policy


class ConnectTokenAppletOptionSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    applet = ObjectRelatedField(read_only=True)
    host = _ConnectionTokenAssetSerializer(read_only=True)
    account = _ConnectionTokenAccountSerializer(read_only=True)
    gateway = _ConnectionTokenGatewaySerializer(read_only=True)
    platform = _ConnectionTokenPlatformSerializer(read_only=True)
    remote_app_option = serializers.JSONField(read_only=True)


class ConnectTokenVirtualAppOptionSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('Name'))
    image_name = serializers.CharField(label=_('Image name'))
    image_port = serializers.IntegerField(label=_('Image port'))
    image_protocol = serializers.CharField(label=_('Image protocol'))
