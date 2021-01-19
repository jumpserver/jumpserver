from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from rest_framework import serializers
from perms.serializers import ActionsField
from perms.models import AssetPermission
from assets.models import Asset, SystemUser
from orgs.utils import tmp_to_org
from tickets.models import Ticket
from .common import DefaultPermissionName


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


class ApproveSerializer(serializers.Serializer):
    # 审批信息
    approve_permission_name = serializers.CharField(
        max_length=128, default=DefaultPermissionName(), label=_('Permission name')
    )
    approve_assets = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(), label=_('Approve assets')
    )
    approve_assets_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve assets display'), allow_null=True,
        default=list,
    )
    approve_system_users = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(),
        label=_('Approve system users')
    )
    approve_system_users_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
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

    def validate_approve_permission_name(self, permission_name):
        if not isinstance(self.root.instance, Ticket):
            return permission_name

        with tmp_to_org(self.root.instance.org_id):
            already_exists = AssetPermission.objects.filter(name=permission_name).exists()
            if not already_exists:
                return permission_name

        raise serializers.ValidationError(_(
            'Permission named `{}` already exists'.format(permission_name)
        ))

    def validate_approve_assets(self, approve_assets):
        if not isinstance(self.root.instance, Ticket):
            return []

        with tmp_to_org(self.root.instance.org_id):
            assets_id = Asset.objects.filter(id__in=approve_assets).values_list('id', flat=True)
            assets_id = [str(asset_id) for asset_id in assets_id]
            if assets_id:
                return assets_id

        raise serializers.ValidationError(_(
            'No `Asset` are found under Organization `{}`'.format(self.root.instance.org_name)
        ))

    def validate_approve_system_users(self, approve_system_users):
        if not isinstance(self.root.instance, Ticket):
            return []

        with tmp_to_org(self.root.instance.org_id):
            queries = Q(protocol__in=SystemUser.ASSET_CATEGORY_PROTOCOLS)
            queries &= Q(id__in=approve_system_users)
            system_users_id = SystemUser.objects.filter(queries).values_list('id', flat=True)
            system_users_id = [str(system_user_id) for system_user_id in system_users_id]
            if system_users_id:
                return system_users_id

        raise serializers.ValidationError(_(
            'No `SystemUser` are found under Organization `{}`'.format(self.root.instance.org_name)
        ))


class ApplyAssetSerializer(ApplySerializer, ApproveSerializer):
    # 推荐信息
    recommend_assets = serializers.SerializerMethodField()
    recommend_system_users = serializers.SerializerMethodField()

    def get_recommend_assets(self, value):
        if not isinstance(self.root.instance, Ticket):
            return []

        apply_ip_group = value.get('apply_ip_group', [])
        apply_hostname_group = value.get('apply_hostname_group', [])
        queries = Q()
        if apply_ip_group:
            queries |= Q(ip__in=apply_ip_group)
        for hostname in apply_hostname_group:
            queries |= Q(hostname__icontains=hostname)
        if not queries:
            return []
        with tmp_to_org(self.root.instance.org_id):
            assets_id = Asset.objects.filter(queries).values_list('id', flat=True)[:5]
            assets_id = [str(asset_id) for asset_id in assets_id]
            return assets_id

    def get_recommend_system_users(self, value):
        if not isinstance(self.root.instance, Ticket):
            return []

        apply_system_user_group = value.get('apply_system_user_group', [])
        if not apply_system_user_group:
            return []

        queries = Q()
        for system_user in apply_system_user_group:
            queries |= Q(username__icontains=system_user)
            queries |= Q(name__icontains=system_user)
        queries &= Q(protocol__in=SystemUser.ASSET_CATEGORY_PROTOCOLS)

        with tmp_to_org(self.root.instance.org_id):
            system_users_id = SystemUser.objects.filter(queries).values_list('id', flat=True)[:5]
            system_users_id = [str(system_user_id) for system_user_id in system_users_id]
            return system_users_id
