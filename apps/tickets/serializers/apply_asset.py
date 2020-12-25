from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from perms.serializers import ActionsField
from perms.models import Action


__all__ = [
    'TicketApplyAssetSerializer', 'TicketNoMetaSerializer'
]


class TicketApplyAssetSerializer(serializers.Serializer):
    # 申请信息
    apply_ip_group = serializers.ListField(
        child=serializers.IPAddressField(), default=list, label=_('IP group')
    )
    apply_hostname_group = serializers.ListField(
        child=serializers.CharField(), default=list, label=_('Hostname group')
    )
    apply_system_user_group = serializers.ListField(
        child=serializers.CharField(), default=list, label=_('System user group')
    )
    apply_actions = ActionsField(
        choices=Action.DB_CHOICES, default=Action.ALL
    )
    apply_date_start = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date expired')
    )
    # 审批信息
    approve_assets = serializers.ListField(
        child=serializers.UUIDField(), default=list, required=False, label=_('Approve assets')
    )
    approve_system_users = serializers.ListField(
        child=serializers.UUIDField(), default=list, required=False, label=_('Approve system users')
    )
    approve_actions = ActionsField(
        choices=Action.DB_CHOICES, default=Action.NONE
    )
    approve_date_start = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date expired')
    )
    # 辅助信息
    # assets_waitlist_url = serializers.SerializerMethodField()
    # system_users_waitlist_url = serializers.SerializerMethodField()

    @staticmethod
    def perform_apply_validate(attrs):
        return {
            name: value
            for name, value in attrs.items()
            if name.startswith('apply_')
        }

    @staticmethod
    def perform_approve_validate(attrs):
        return {
            name: value
            for name, value in attrs.items()
            if name.startswith('approve_')
        }

    def validate(self, attrs):
        view_action = self.context['view'].action
        if view_action == 'apply':
            attrs = self.perform_apply_validate(attrs)
        elif view_action == 'approve':
            attrs = self.perform_approve_validate(attrs)
        elif view_action == 'reject':
            attrs = {}
        elif view_action == 'close':
            attrs = {}
        else:
            attrs = {}
        return attrs


class TicketNoMetaSerializer(serializers.Serializer):
    pass
