from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from perms.serializers import ActionsField
from perms.models import Action
from assets.models import Asset, SystemUser
from orgs.utils import tmp_to_org
from .mixin import TicketMetaSerializerMixin


__all__ = [
    'TicketMetaApplyAssetSerializer',
    'TicketMetaApplyAssetApplySerializer',
    'TicketMetaApplyAssetApproveSerializer',
]


class TicketMetaApplyAssetSerializer(TicketMetaSerializerMixin, serializers.Serializer):
    # 申请信息
    apply_ip_group = serializers.ListField(
        child=serializers.IPAddressField(), allow_null=True, default=list, label=_('IP group')
    )
    apply_hostname_group = serializers.ListField(
        child=serializers.CharField(), allow_null=True, default=list, label=_('Hostname group')
    )
    apply_system_user_group = serializers.ListField(
        child=serializers.CharField(), allow_null=True, default=list, label=_('System user group')
    )
    apply_actions = ActionsField(
        choices=Action.DB_CHOICES, allow_null=True, default=Action.ALL
    )
    apply_date_start = serializers.DateTimeField(
        allow_null=True, required=True, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        allow_null=True, required=True, label=_('Date expired')
    )
    # 审批信息
    approve_assets = serializers.ListField(
        child=serializers.UUIDField(), required=True, allow_null=True, label=_('Approve assets')
    )
    approve_system_users = serializers.ListField(
        child=serializers.UUIDField(), required=True, allow_null=True, label=_('Approve system users')
    )
    approve_actions = ActionsField(
        choices=Action.DB_CHOICES, allow_null=True, default=Action.NONE
    )
    approve_date_start = serializers.DateTimeField(
        required=True, allow_null=True, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, allow_null=True, label=_('Date expired')
    )


class TicketMetaApplyAssetApplySerializer(TicketMetaApplyAssetSerializer):
    need_fields_prefix = 'apply_'


class TicketMetaApplyAssetApproveSerializer(TicketMetaApplyAssetSerializer):
    need_fields_prefix = 'approve_'

    def validate_approve_assets(self, approve_assets_id):
        org_id = self.root.instance.org_id
        org_name = self.root.instance.org_name
        with tmp_to_org(org_id):
            valid_approve_assets = Asset.objects.filter(id__in=approve_assets_id)
        if not valid_approve_assets:
            error = _('None of the approved assets belong to Organization `{}`'.format(org_name))
            raise serializers.ValidationError(error)
        return valid_approve_assets

    def validate_approve_system_users(self, approve_system_users_id):
        org_id = self.root.instance.org_id
        org_name = self.root.instance.org_name
        with tmp_to_org(org_id):
            valid_approve_system_users = SystemUser.objects.filter(id__in=approve_system_users_id)
        if not valid_approve_system_users:
            error = _(
                'None of the approved system users belong to Organization `{}`'.format(org_name)
            )
            raise serializers.ValidationError(error)
        return valid_approve_system_users
