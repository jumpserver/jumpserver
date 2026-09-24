from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.models import Asset, Node
from common.serializers.fields import ObjectRelatedField
from orgs.utils import tmp_to_org
from perms.models import AssetPermission
from perms.serializers.permission import ActionChoicesField
from perms.utils.expire_soon_notice import sync_ticket_expire_soon_notice
from tickets.models import Ticket
from .common import AssetRequestValidationMixin
from .ticket import TicketApplySerializer

__all__ = ['ApplyAssetSerializer']


asset_or_node_help_text = _('Select at least one asset or node')
apply_help_text = _('Support fuzzy search, and display up to 10 items')


class ApplyAssetSerializer(AssetRequestValidationMixin, TicketApplySerializer):
    """Keep the rich asset form while storing its fields on the base ticket."""
    apply_users = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=False,
        max_length=100, write_only=True, label=_('Authorized users'),
    )
    apply_assets = ObjectRelatedField(
        queryset=Asset.objects, many=True, required=False, write_only=True,
        label=_('Apply assets'), help_text=apply_help_text,
    )
    apply_nodes = ObjectRelatedField(
        queryset=Node.objects, many=True, required=False, write_only=True,
        label=_('Apply nodes'), help_text=apply_help_text,
    )
    apply_accounts = serializers.ListField(
        child=serializers.CharField(max_length=128), allow_empty=False,
        write_only=True, label=_('Apply accounts'),
    )
    apply_actions = ActionChoicesField(required=True, allow_null=False, write_only=True, label=_('Apply actions'))
    apply_date_start = serializers.DateTimeField(write_only=True, label=_('Date start'))
    apply_date_expired = serializers.DateTimeField(write_only=True, label=_('Date expired'))
    apply_expire_soon_notice_minutes = serializers.IntegerField(
        min_value=1, required=False, allow_null=True, write_only=True,
        label=_('Expiration-soon notice minutes'),
    )
    class Meta(TicketApplySerializer.Meta):
        model = Ticket
        fields = TicketApplySerializer.Meta.fields + [
            'apply_users', 'apply_assets', 'apply_nodes', 'apply_accounts',
            'apply_actions', 'apply_date_start', 'apply_date_expired',
            'apply_expire_soon_notice_minutes',
        ]

    def validate_apply_nodes(self, nodes):
        return self.filter_many_to_many_field(Node, nodes)

    def validate_apply_assets(self, assets):
        return self.filter_many_to_many_field(Asset, assets)

    def validate(self, attrs):
        attrs['type'] = 'apply_asset'
        attrs = super().validate(attrs)
        from tickets.workflow.approvers import available_users
        users = list(dict.fromkeys(attrs.pop('apply_users', [attrs['applicant'].pk])))
        if available_users(attrs['org_id']).filter(pk__in=users).count() != len(users):
            raise serializers.ValidationError({'apply_users': _('Select active organization members.')})
        try:
            sync_ticket_expire_soon_notice(None, attrs)
        except DjangoValidationError as exc:
            field_mapping = {
                'date_expired': 'apply_date_expired',
                'expire_soon_notice_minutes': 'apply_expire_soon_notice_minutes',
            }
            raise serializers.ValidationError({
                field_mapping.get(key, key): value for key, value in exc.message_dict.items()
            }) from exc
        if not attrs.get('apply_nodes') and not attrs.get('apply_assets'):
            raise serializers.ValidationError({
                'apply_nodes': asset_or_node_help_text,
                'apply_assets': asset_or_node_help_text,
            })
        attrs['request_data'] = {
            'apply_users': [str(pk) for pk in users],
            'apply_assets': [str(pk) for pk in attrs.pop('apply_assets', [])],
            'apply_nodes': [str(pk) for pk in attrs.pop('apply_nodes', [])],
            'apply_accounts': attrs.pop('apply_accounts'),
            'apply_actions': attrs.pop('apply_actions'),
            'apply_date_start': attrs.pop('apply_date_start').isoformat(),
            'apply_date_expired': attrs.pop('apply_date_expired').isoformat(),
            'apply_expire_soon_notice_minutes': attrs.pop('apply_expire_soon_notice_minutes', None),
        }
        return attrs

    def create(self, validated_data):
        ticket = Ticket.objects.create(**validated_data)
        name = self._get_permission_name(ticket)
        with tmp_to_org(ticket.org_id):
            if AssetPermission.objects.filter(name=name).exists():
                raise serializers.ValidationError(_('Permission named `{}` already exists').format(name))
        ticket.request_data['apply_permission_name'] = name
        ticket.save(update_fields=['request_data'])
        return ticket
