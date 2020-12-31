from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from perms.serializers import ActionsField
from assets.models import Asset, SystemUser
from .base import BaseTicketMetaApproveSerializerMixin
from tickets.models import Ticket

from common.fields.serializer import JSONFieldModelSerializer


__all__ = [
    'TicketMetaApplyAssetSerializer',
    'TicketMetaApplyAssetApplySerializer',
    'TicketMetaApplyAssetApproveSerializer',
]


class TicketMetaApplyAssetSerializer(JSONFieldModelSerializer):
    # 申请信息
    apply_ip_group = serializers.ListField(
        required=False, child=serializers.IPAddressField(), label=_('IP group'),
        default=list,
    )
    apply_hostname_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('Hostname group'),
        default=list,
    )
    apply_system_user_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('System user group'),
        default=list,
    )
    apply_actions = ActionsField(
        required=True
    )
    apply_actions_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve assets display'),
        default=list,
    )
    apply_date_start = serializers.DateTimeField(
        required=True, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired')
    )
    # 审批信息
    approve_assets = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Approve assets')
    )
    approve_assets_snapshot = serializers.ListField(
        required=False, read_only=True, child=serializers.DictField(),
        label=_('Approve assets display'),
        default=list,
    )
    approve_system_users = serializers.ListField(
        required=True, child=serializers.UUIDField(), label=_('Approve system users')
    )
    approve_system_users_snapshot = serializers.ListField(
        required=False, read_only=True, child=serializers.DictField(),
        label=_('Approve assets display'),
        default=list,
    )
    approve_actions = ActionsField(
        required=True
    )
    approve_actions_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve assets display'),
        default=list,
    )
    approve_date_start = serializers.DateTimeField(
        required=True, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired')
    )

    class Meta:
        model = Ticket
        model_field = Ticket.meta
        fields = [
            'apply_ip_group',
            'apply_hostname_group', 'apply_system_user_group',
            'apply_actions', 'apply_actions_display',
            'apply_date_start', 'apply_date_expired',

            'approve_assets', 'approve_assets_snapshot',
            'approve_system_users', 'approve_system_users_snapshot',
            'approve_actions', 'approve_actions_display',
            'approve_date_start', 'approve_date_expired',
        ]
        read_only_fields = fields


class TicketMetaApplyAssetApplySerializer(TicketMetaApplyAssetSerializer):

    class Meta(TicketMetaApplyAssetSerializer.Meta):
        required_fields = [
            'apply_ip_group', 'apply_hostname_group', 'apply_system_user_group',
            'apply_actions', 'apply_date_start', 'apply_date_expired',
        ]
        read_only_fields = list(
            set(TicketMetaApplyAssetSerializer.Meta.fields) - set(required_fields)
        )


class TicketMetaApplyAssetApproveSerializer(BaseTicketMetaApproveSerializerMixin,
                                            TicketMetaApplyAssetSerializer):

    class Meta(TicketMetaApplyAssetSerializer.Meta):
        required_fields = [
            'approve_assets', 'approve_system_users', 'approve_actions',
            'approve_date_start', 'approve_date_expired',
        ]
        read_only_fields = list(
            set(TicketMetaApplyAssetSerializer.Meta.fields) - set(required_fields)
        )

    def validate_approve_assets(self, approve_assets):
        assets_id = self.filter_approve_resources(resource_model=Asset, resources_id=approve_assets)
        return assets_id

    def validate_approve_system_users(self, approve_system_users):
        queries = {'protocol__in': SystemUser.ASSET_CATEGORY_PROTOCOLS}
        system_users_id = self.filter_approve_system_users(approve_system_users, queries)
        return system_users_id
