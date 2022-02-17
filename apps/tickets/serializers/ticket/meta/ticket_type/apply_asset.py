from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from perms.serializers.base import ActionsField
from perms.models import AssetPermission
from orgs.utils import tmp_to_org
from tickets.models import Ticket
from .common import DefaultPermissionName

__all__ = [
    'ApplySerializer',
]

asset_or_node_help_text = _("Select at least one asset or node")


class ApplySerializer(serializers.Serializer):
    apply_permission_name = serializers.CharField(
        max_length=128, default=DefaultPermissionName(), label=_('Apply name')
    )
    apply_nodes = serializers.ListField(
        required=False, allow_null=True, child=serializers.UUIDField(),
        label=_('Apply nodes'), help_text=asset_or_node_help_text,
        default=list
    )
    apply_nodes_display = serializers.ListField(
        child=serializers.CharField(), label=_('Apply nodes display'), required=False
    )
    # 申请信息
    apply_assets = serializers.ListField(
        required=False, allow_null=True, child=serializers.UUIDField(),
        label=_('Apply assets'), help_text=asset_or_node_help_text
    )
    apply_assets_display = serializers.ListField(
        required=False, read_only=True, child=serializers.CharField(),
        label=_('Apply assets display'), allow_null=True,
        default=list
    )
    apply_system_users = serializers.ListField(
        required=True, allow_null=True, child=serializers.UUIDField(),
        label=_('Apply system users')
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

    def validate(self, attrs):
        if not attrs.get('apply_nodes') and not attrs.get('apply_assets'):
            raise serializers.ValidationError({
                'apply_nodes': asset_or_node_help_text,
                'apply_assets': asset_or_node_help_text,
            })

        apply_date_start = attrs['apply_date_start'].strftime('%Y-%m-%d %H:%M:%S')
        apply_date_expired = attrs['apply_date_expired'].strftime('%Y-%m-%d %H:%M:%S')

        if apply_date_expired <= apply_date_start:
            error = _('The expiration date should be greater than the start date')
            raise serializers.ValidationError({'apply_date_expired': error})

        attrs['apply_date_start'] = apply_date_start
        attrs['apply_date_expired'] = apply_date_expired
        return attrs
