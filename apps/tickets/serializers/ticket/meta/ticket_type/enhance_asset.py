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
    apply_host = serializers.CharField(required=True, label=_('Host'), allow_null=True, write_only=True)
    enchance_host_display = serializers.CharField(required=False, allow_null=True, read_only=True)
    apply_system_users = serializers.ListField(
        required=False, child=serializers.CharField(), label=_('System user'),
        default=list, allow_null=True, write_only=True
    )
    enchance_system_users_display = serializers.ListField(
        required=False, child=serializers.CharField(),
        default=list, allow_null=True, read_only=True
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
    approve_asset = serializers.UUIDField(
        required=True, allow_null=True, label=_('Approve assets')
    )
    approve_asset_display = serializers.CharField(read_only=True, label=_('Approve assets display'))
    approve_system_users = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(),
        label=_('Approve system users')
    )
    approve_system_users_display = serializers.ListField(
        child=serializers.CharField(), read_only=True, label=_('Approve assets display')
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

    def validate_approve_assets(self, approve_asset):
        if not isinstance(self.root.instance, Ticket):
            return []

        with tmp_to_org(self.root.instance.org_id):
            asset_id = Asset.objects.filter(id=approve_asset).first()
            if asset_id:
                return str(approve_asset)

        raise serializers.ValidationError(_(
            'No `Asset` are found under Organization `{}`'.format(self.root.instance.org_name)
        ))

    def validate_approve_system_users(self, approve_system_users):
        if not isinstance(self.root.instance, Ticket):
            return []

        with tmp_to_org(self.root.instance.org_id):
            queries = Q(protocol__in=SystemUser.ASSET_CATEGORY_PROTOCOLS)
            queries &= Q(id__in=approve_system_users)
            system_user_ids = SystemUser.objects.filter(queries).values_list('id', flat=True)
            system_user_ids = [str(system_user_id) for system_user_id in system_user_ids]
            if system_user_ids:
                return system_user_ids

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

        asset_id = value.get('apply_host', '')
        return asset_id

    def get_recommend_system_users(self, value):
        if not isinstance(self.root.instance, Ticket):
            return []

        system_users = value.get('apply_system_users', [])
        return system_users
