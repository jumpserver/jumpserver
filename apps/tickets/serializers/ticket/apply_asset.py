from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import Asset, Node
from common.drf.fields import ObjectRelatedField
from perms.models import AssetPermission
from perms.serializers.permission import ActionChoicesField
from tickets.models import ApplyAssetTicket
from .common import BaseApplyAssetSerializer
from .ticket import TicketApplySerializer

__all__ = ['ApplyAssetSerializer']

asset_or_node_help_text = _("Select at least one asset or node")


class ApplyAssetSerializer(BaseApplyAssetSerializer, TicketApplySerializer):
    apply_assets = ObjectRelatedField(queryset=Asset.objects, many=True, required=False, label=_('Apply assets'))
    apply_nodes = ObjectRelatedField(queryset=Node.objects, many=True, required=False, label=_('Apply nodes'))
    apply_actions = ActionChoicesField(required=False, allow_null=True, label=_("Apply actions"))
    permission_model = AssetPermission

    class Meta(TicketApplySerializer.Meta):
        model = ApplyAssetTicket
        fields_mini = ['id', 'title']
        writeable_fields = [
            'id', 'title', 'apply_nodes', 'apply_assets',
            'apply_accounts', 'apply_actions', 'org_id', 'comment',
            'apply_date_start', 'apply_date_expired'
        ]
        fields = TicketApplySerializer.Meta.fields + writeable_fields + ['apply_permission_name', ]
        read_only_fields = list(set(fields) - set(writeable_fields))
        ticket_extra_kwargs = TicketApplySerializer.Meta.extra_kwargs
        extra_kwargs = {
            'apply_nodes': {'required': False},
            'apply_assets': {'required': False},
            'apply_accounts': {'required': False},
        }
        extra_kwargs.update(ticket_extra_kwargs)

    def validate_apply_nodes(self, nodes):
        return self.filter_many_to_many_field(Node, nodes)

    def validate_apply_assets(self, assets):
        return self.filter_many_to_many_field(Asset, assets)

    def validate(self, attrs):
        attrs['type'] = 'apply_asset'
        attrs = super().validate(attrs)
        if self.is_final_approval and (
                not attrs.get('apply_nodes')
                and not attrs.get('apply_assets')
        ):
            raise serializers.ValidationError({
                'apply_nodes': asset_or_node_help_text,
                'apply_assets': asset_or_node_help_text,
            })

        return attrs

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related('apply_nodes', 'apply_assets')
        return queryset
