from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Asset, Node
from common.serializers.fields import ObjectRelatedField
from perms.models import AssetPermission
from perms.serializers.permission import ActionChoicesField
from perms.utils.expire_soon_notice import sync_ticket_expire_soon_notice
from tickets.models import ApplyAssetTicket
from .common import BaseApplyAssetSerializer
from .ticket import TicketApplySerializer

__all__ = ['ApplyAssetSerializer', 'ApproveAssetSerializer']

asset_or_node_help_text = _("Select at least one asset or node")

apply_help_text = _('Support fuzzy search, and display up to 10 items')


class ApplyAssetSerializer(BaseApplyAssetSerializer, TicketApplySerializer):
    apply_assets = ObjectRelatedField(
        queryset=Asset.objects, many=True, required=False,
        label=_('Apply assets'), help_text=apply_help_text
    )
    apply_nodes = ObjectRelatedField(
        queryset=Node.objects, many=True, required=False,
        label=_('Apply nodes'), help_text=apply_help_text
    )
    apply_actions = ActionChoicesField(required=False, allow_null=True, label=_("Apply actions"))
    permission_model = AssetPermission

    class Meta(TicketApplySerializer.Meta):
        model = ApplyAssetTicket
        writeable_fields = [
            'id', 'title', 'type', 'flow_id', 'apply_nodes', 'apply_assets',
            'apply_accounts', 'apply_actions', 'apply_date_start',
            'apply_date_expired', 'apply_expire_soon_notice_enabled',
            'apply_expire_soon_notice_minutes', 'comment', 'org_id'
        ]
        read_only_fields = TicketApplySerializer.Meta.read_only_fields + ['apply_permission_name', ]
        fields = TicketApplySerializer.Meta.fields_small + \
                 TicketApplySerializer.Meta.fields_m2m + writeable_fields + read_only_fields
        ticket_extra_kwargs = TicketApplySerializer.Meta.extra_kwargs
        extra_kwargs = {
            'apply_accounts': {'required': False},
            'apply_date_start': {'required': True, 'allow_null': False},
            'apply_date_expired': {'required': True, 'allow_null': False},
        }
        extra_kwargs.update(ticket_extra_kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.set_actions_field()

    def validate_apply_nodes(self, nodes):
        return self.filter_many_to_many_field(Node, nodes)

    def validate_apply_assets(self, assets):
        return self.filter_many_to_many_field(Asset, assets)

    def set_actions_field(self):
        actions = self.fields.get("apply_actions")
        if not actions:
            return
        actions.default = ['connect']

    def validate(self, attrs):
        attrs['type'] = 'apply_asset'
        attrs = super().validate(attrs)
        try:
            sync_ticket_expire_soon_notice(
                self.instance,
                attrs,
                default_enabled=False,
                default_minutes=settings.PERM_EXPIRED_SOON_NOTICE_MINUTES,
                allow_past=self.instance is not None,
            )
        except DjangoValidationError as exc:
            field_mapping = {
                'date_expired': 'apply_date_expired',
                'expire_soon_notice_minutes': 'apply_expire_soon_notice_minutes',
            }
            errors = {
                field_mapping.get(key, key): value
                for key, value in exc.message_dict.items()
            }
            raise serializers.ValidationError(errors) from exc
        if self.is_final_approval and (
                not attrs.get('apply_nodes') and not attrs.get('apply_assets')
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


class ApproveAssetSerializer(ApplyAssetSerializer):
    class Meta(ApplyAssetSerializer.Meta):
        read_only_fields = TicketApplySerializer.Meta.fields_small + \
                           ApplyAssetSerializer.Meta.read_only_fields
