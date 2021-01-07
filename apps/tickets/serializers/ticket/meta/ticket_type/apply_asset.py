from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from rest_framework import serializers
from perms.serializers import ActionsField
from assets.models import Asset, SystemUser
from .mixin import BaseApproveSerializerMixin


__all__ = [
    'ApplyAssetSerializer', 'ApplySerializer', 'ApproveSerializer',
]


class ApplySerializer(serializers.Serializer):
    # 申请信息
    apply_ip_group = serializers.ListField(
        required=False, child=serializers.IPAddressField(), label=_('IP group'),
        default=list, allow_null=True,
    )
    apply_hostname_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('Hostname group'),
        default=list, allow_null=True,
    )
    apply_system_user_group = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('System user group'),
        default=list, allow_null=True
    )
    apply_actions = ActionsField(
        required=True, allow_null=True
    )
    apply_actions_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve assets display'), allow_null=True,
        default=list,
    )
    apply_date_start = serializers.DateTimeField(
        required=True, label=_('Date start'), allow_null=True,
    )
    apply_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired'), allow_null=True,
    )
    # 推荐信息
    recommend_assets = serializers.SerializerMethodField()
    recommend_system_users = serializers.SerializerMethodField()

    @staticmethod
    def get_recommend_assets(value):
        apply_ip_group = value.get('apply_ip_group', [])
        apply_hostname_group = value.get('apply_hostname_group', [])
        queries = Q(ip__in=apply_ip_group)
        for hostname in apply_hostname_group:
            queries |= Q(hostname__icontains=hostname)

        assets_id = Asset.objects.filter(queries).values_list('id', flat=True)[:5]
        assets_id = [str(asset_id) for asset_id in assets_id]
        return assets_id

    @staticmethod
    def get_recommend_system_users(value):
        apply_system_user_group = value.get('apply_system_user_group', [])
        queries = Q()
        for system_user in apply_system_user_group:
            queries |= Q(username__icontains=system_user)
            queries |= Q(name__icontains=system_user)
        queries &= Q(protocol__in=SystemUser.ASSET_CATEGORY_PROTOCOLS)

        system_users_id = SystemUser.objects.filter(queries).values_list('id', flat=True)[:5]
        system_users_id = [str(system_user_id) for system_user_id in system_users_id]
        return system_users_id


class ApproveSerializer(BaseApproveSerializerMixin, serializers.Serializer):
    # 审批信息
    approve_assets = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(), label=_('Approve assets')
    )
    approve_assets_snapshot = serializers.ListField(
        required=False, read_only=True, child=serializers.DictField(),
        label=_('Approve assets display'), allow_null=True,
        default=list,
    )
    approve_system_users = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(),
        label=_('Approve system users')
    )
    approve_system_users_snapshot = serializers.ListField(
        required=False, read_only=True, child=serializers.DictField(),
        label=_('Approve assets display'), allow_null=True,
        default=list,
    )
    approve_actions = ActionsField(
        required=True, allow_null=True,
    )
    approve_actions_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve assets display'), allow_null=True,
        default=list,
    )
    approve_date_start = serializers.DateTimeField(
        required=True, label=_('Date start'), allow_null=True,
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired'), allow_null=True
    )

    def validate_approve_assets(self, approve_assets):
        assets_id = self.filter_approve_resources(resource_model=Asset, resources_id=approve_assets)
        return assets_id

    def validate_approve_system_users(self, approve_system_users):
        queries = {'protocol__in': SystemUser.ASSET_CATEGORY_PROTOCOLS}
        system_users_id = self.filter_approve_system_users(approve_system_users, queries)
        return system_users_id


class ApplyAssetSerializer(ApplySerializer, ApproveSerializer):
    pass
