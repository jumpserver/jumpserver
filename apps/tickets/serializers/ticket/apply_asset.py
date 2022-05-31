from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from perms.serializers.base import ActionsField
from perms.models import AssetPermission

from tickets.models import ApplyAssetTicket
from .ticket import TicketApplySerializer
from .common import BaseApplyAssetApplicationSerializer

__all__ = ['ApplyAssetSerializer', 'ApplyAssetDisplaySerializer']

asset_or_node_help_text = _("Select at least one asset or node")


class ApplyAssetSerializer(BaseApplyAssetApplicationSerializer, TicketApplySerializer):
    apply_actions = ActionsField(required=True, allow_null=True)
    permission_model = AssetPermission

    class Meta:
        model = ApplyAssetTicket
        writeable_fields = [
            'id', 'title', 'type', 'apply_permission_name', 'apply_nodes', 'apply_assets',
            'apply_system_users', 'apply_actions', 'apply_actions_display',
            'apply_date_start', 'apply_date_expired', 'org_id'
        ]
        fields = TicketApplySerializer.Meta.fields + writeable_fields
        read_only_fields = list(set(fields) - set(writeable_fields))
        extra_kwargs = TicketApplySerializer.Meta.extra_kwargs

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get('apply_nodes') and not attrs.get('apply_assets'):
            raise serializers.ValidationError({
                'apply_nodes': asset_or_node_help_text,
                'apply_assets': asset_or_node_help_text,
            })
        return attrs


class ApplyAssetDisplaySerializer(ApplyAssetSerializer):
    class Meta:
        model = ApplyAssetSerializer.Meta.model
        fields = ApplyAssetSerializer.Meta.fields
        read_only_fields = fields
