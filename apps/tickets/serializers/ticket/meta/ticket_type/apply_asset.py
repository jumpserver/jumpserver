from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from perms.serializers import ActionsField
from perms.models import AssetPermission
from orgs.utils import tmp_to_org
from tickets.models import Ticket
from .common import DefaultPermissionName

__all__ = [
    'ApplySerializer',
]


class ApplySerializer(serializers.Serializer):
    apply_permission_name = serializers.CharField(
        max_length=128, default=DefaultPermissionName(), label=_('Apply name')
    )
    # 申请信息
    apply_assets = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(), label=_('Apply assets')
    )
    apply_assets_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Approve assets display'), allow_null=True,
        default=list,
    )
    apply_system_users = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(),
        label=_('Approve system users')
    )
    apply_system_users_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Apply assets display'), allow_null=True,
        default=list,
    )
    apply_actions = ActionsField(
        required=True, allow_null=True
    )
    apply_actions_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Apply assets display'), allow_null=True,
        default=list,
    )
    apply_date_start = serializers.DateTimeField(
        required=True, label=_('Date start'), allow_null=True,
    )
    apply_date_expired = serializers.DateTimeField(
        required=True, label=_('Date expired'), allow_null=True,
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
