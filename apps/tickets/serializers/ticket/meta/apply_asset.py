from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from perms.serializers import ActionsField
from assets.models import Asset, SystemUser
from tickets.models import Ticket
from .mixin import BaseApproveSerializerMixin


__all__ = [
    'ApplyAssetTypeSerializer', 'ApplySerializer', 'ApproveSerializer',
]


class ApplySerializer(serializers.Serializer):
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


class ApproveSerializer(BaseApproveSerializerMixin, serializers.Serializer):
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

    def validate_approve_assets(self, approve_assets):
        assets_id = self.filter_approve_resources(resource_model=Asset, resources_id=approve_assets)
        return assets_id

    def validate_approve_system_users(self, approve_system_users):
        queries = {'protocol__in': SystemUser.ASSET_CATEGORY_PROTOCOLS}
        system_users_id = self.filter_approve_system_users(approve_system_users, queries)
        return system_users_id


class ApplyAssetTypeSerializer(ApplySerializer, ApproveSerializer):
    pass
