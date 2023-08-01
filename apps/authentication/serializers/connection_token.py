from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import CommonModelSerializer
from common.serializers.fields import EncryptedField
from perms.serializers.permission import ActionChoicesField
from ..models import ConnectionToken

__all__ = [
    'ConnectionTokenSerializer', 'SuperConnectionTokenSerializer',
    'ConnectionTokenReusableSerializer',
]


class ConnectionTokenSerializer(CommonModelSerializer):
    expire_time = serializers.IntegerField(read_only=True, label=_('Expired time'))
    input_secret = EncryptedField(
        label=_("Input secret"), max_length=40960, required=False, allow_blank=True
    )
    from_ticket_info = serializers.SerializerMethodField(label=_("Ticket info"))
    actions = ActionChoicesField(read_only=True, label=_("Actions"))

    class Meta:
        model = ConnectionToken
        fields_mini = ['id', 'value']
        fields_small = fields_mini + [
            'user', 'asset', 'account', 'input_username', 'input_secret',
            'connect_method', 'connect_options', 'protocol', 'actions',
            'is_active', 'is_reusable', 'from_ticket', 'from_ticket_info',
            'date_expired', 'date_created', 'date_updated', 'created_by',
            'updated_by', 'org_id', 'org_name',
        ]
        read_only_fields = [
            # 普通 Token 不支持指定 user
            'user', 'expire_time', 'is_expired', 'date_expired',
            'user_display', 'asset_display',
        ]
        fields = fields_small + read_only_fields
        extra_kwargs = {
            'from_ticket': {'read_only': True},
            'value': {'read_only': True},
            'is_expired': {'read_only': True, 'label': _('Is expired')},
        }

    def get_request_user(self):
        request = self.context.get('request')
        user = request.user if request else None
        return user

    def get_user(self, attrs):
        return self.get_request_user()

    def get_from_ticket_info(self, instance):
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
