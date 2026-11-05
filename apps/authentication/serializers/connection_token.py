from collections.abc import Mapping

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.utils import validate_account_username
from accounts.const import AliasAccount
from common.utils import get_request_ip_or_data
from common.serializers import CommonModelSerializer
from common.serializers.fields import EncryptedField
from perms.serializers.permission import ActionChoicesField
from ..models import ConnectionToken, AdminConnectionToken
from orgs.mixins.serializers import OrgResourceModelSerializerMixin

__all__ = [
    'ConnectionTokenSerializer', 'SuperConnectionTokenSerializer',
    'ConnectionTokenReusableSerializer', 'AdminConnectionTokenSerializer',
]


class ConnectionACLInputSerializer(serializers.Serializer):
    step = serializers.ChoiceField(
        choices=('reason', 'mfa', 'face', 'review', 'push_account', 'face_online'), required=False,
    )
    reason = serializers.CharField(required=False, allow_blank=False, max_length=4096)
    mfa_type = serializers.CharField(required=False, max_length=32)
    mfa_code = serializers.CharField(required=False, max_length=4096, trim_whitespace=False)
    mfa_send = serializers.BooleanField(required=False, default=False)
    cancel = serializers.BooleanField(required=False, default=False)
    retry_face = serializers.BooleanField(required=False, default=False)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({
                    field: _('This field cannot be submitted.') for field in sorted(unknown)
                })
        return super().to_internal_value(data)

    def validate(self, attrs):
        step = attrs.get('step')
        if step:
            fields = {
                'reason': {'reason'}, 'mfa': {'mfa_type', 'mfa_code', 'mfa_send'},
                'face': {'retry_face'}, 'review': set(), 'push_account': set(),
                'face_online': set(),
            }
            unexpected = set(self.initial_data) - fields[step] - {'step', 'cancel'}
            if unexpected:
                raise serializers.ValidationError({
                    field: _('This field does not belong to the current step.')
                    for field in sorted(unexpected)
                })
        return attrs


class ConnectionACLBatchInputSerializer(ConnectionACLInputSerializer):
    token_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1, max_length=100)
    step = serializers.ChoiceField(choices=('mfa', 'face', 'review', 'face_online'))

    def validate(self, attrs):
        if len(set(attrs['token_ids'])) != len(attrs['token_ids']):
            raise serializers.ValidationError({'token_ids': _('Duplicate connection tokens.')})
        # Validate the step payload with the same allowlist as individual connections.
        payload = {key: value for key, value in self.initial_data.items() if key != 'token_ids'}
        serializer = ConnectionACLInputSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get('cancel'):
            raise serializers.ValidationError({'cancel': _('Cancel connections individually.')})
        return attrs


class ConnectionTokenSerializer(OrgResourceModelSerializerMixin):
    account_preparation_required = serializers.SerializerMethodField()
    acl = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    expire_time = serializers.IntegerField(read_only=True, label=_('Expired time'))
    input_secret = EncryptedField(
        label=_("Input secret"), max_length=40960, required=False, allow_blank=True
    )
    from_ticket_info = serializers.SerializerMethodField(label=_("Ticket info"))
    actions = ActionChoicesField(read_only=True, label=_("Actions"))
    save_personal_credential = serializers.BooleanField(
        required=False, default=False, write_only=True,
        label=_("Save personal credential"),
    )
    personal_credential_version = serializers.IntegerField(
        required=False, min_value=1, write_only=True,
        label=_("Personal credential version"),
    )

    class Meta:
        model = ConnectionToken
        fields_mini = ['id', 'value']
        fields_small = fields_mini + [
            'user', 'asset', 'account', 'input_username', 'input_secret', 'input_secret_type',
            'personal_credential_id', 'personal_credential_version',
            'save_personal_credential',
            'connect_method', 'connect_options', 'protocol', 'actions',
            'is_active', 'is_reusable', 'from_ticket', 'from_ticket_info',
            'date_expired', 'date_created', 'date_updated', 'created_by',
            'updated_by', 'org_id', 'org_name', 'face_monitor_token',
            'remote_addr', 'acl', 'account_preparation_required',
            'comment',
        ]
        read_only_fields = [
            # 普通 Token 不支持指定 user
            'user', 'expire_time', 'is_expired', 'date_expired',
            'user_display', 'asset_display', 'is_active',
            'comment',
        ]
        fields = fields_small + read_only_fields
        extra_kwargs = {
            'face_monitor_token': {'read_only': True},
            'personal_credential_id': {'required': False, 'allow_null': True},
            'from_ticket': {'read_only': True},
            'value': {'read_only': True},
            'is_expired': {'read_only': True, 'label': _('Is expired')},
            'org_name': {'label': _("Org name")},
        }

    @staticmethod
    def get_account_preparation_required(instance):
        return (instance.acl_context or {}).get('requirements', {}).get('push_account') in ('pending', 'running', 'failed')

    @staticmethod
    def get_is_active(instance):
        return instance.is_active and instance.acl_ready

    @staticmethod
    def get_acl(instance):
        from authentication.services.connection_acl import acl_state
        return acl_state(instance)

    def get_request_user(self):
        request = self.context.get('request')
        user = request.user if request else None
        return user

    def get_user(self, attrs):
        return self.get_request_user()

    @staticmethod
    def validate_input_username(value):
        return validate_account_username(value)

    def validate(self, attrs):
        if self.instance and attrs:
            raise serializers.ValidationError(_('Connection parameters cannot be changed; create a new connection token'))
        if attrs.get('account') == AliasAccount.USER and attrs.get('input_username'):
            raise serializers.ValidationError({'input_username': _('The same-name account username is determined by the server.')})
        return super().validate(attrs)

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['remote_addr'] = get_request_ip_or_data(request)
        return super().create(validated_data)

    def get_from_ticket_info(self, instance) -> dict:
        if not instance.from_ticket:
            return {}
        user = self.get_request_user()
        info = instance.from_ticket.get_extra_info_of_review(user=user)
        return info


class ConnectionTokenReusableSerializer(CommonModelSerializer):
    class Meta:
        model = ConnectionToken
        fields = ['id', 'date_expired', 'is_reusable']
        can_update_fields = ['is_reusable']
        read_only_fields = list(set(fields) - set(can_update_fields))


class SuperConnectionTokenSerializer(ConnectionTokenSerializer):
    class Meta(ConnectionTokenSerializer.Meta):
        read_only_fields = list(set(ConnectionTokenSerializer.Meta.read_only_fields) - {'user'})

    def get_user(self, attrs):
        return attrs.get('user')


class AdminConnectionTokenSerializer(ConnectionTokenSerializer):
    class Meta(ConnectionTokenSerializer.Meta):
        model = AdminConnectionToken
