from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from perms.serializers.base import ActionsField
from perms.models import AssetPermission
from orgs.utils import tmp_to_org
from assets.models import Asset, Node

from tickets.models import ApplyAssetTicket
from .ticket import TicketApplySerializer
from .common import BaseApplyAssetApplicationSerializer

__all__ = ['ApplyAssetSerializer', 'ApplyAssetDisplaySerializer', 'ApproveAssetSerializer']

asset_or_node_help_text = _("Select at least one asset or node")


class ApplyAssetSerializer(BaseApplyAssetApplicationSerializer, TicketApplySerializer):
    apply_actions = ActionsField(required=True, allow_empty=False)
    permission_model = AssetPermission

    class Meta:
        model = ApplyAssetTicket
        writeable_fields = [
            'id', 'title', 'type', 'apply_nodes', 'apply_assets',
            'apply_system_users', 'apply_actions', 'comment',
            'apply_date_start', 'apply_date_expired', 'org_id'
        ]
        fields = TicketApplySerializer.Meta.fields + \
                 writeable_fields + ['apply_permission_name', 'apply_actions_display']
        read_only_fields = list(set(fields) - set(writeable_fields))
        ticket_extra_kwargs = TicketApplySerializer.Meta.extra_kwargs
        extra_kwargs = {
            'apply_nodes': {'required': False, 'allow_empty': True},
            'apply_assets': {'required': False, 'allow_empty': True},
            'apply_system_users': {'required': False, 'allow_empty': True},
        }
        extra_kwargs.update(ticket_extra_kwargs)

    def validate_apply_nodes(self, nodes):
        return self.filter_many_to_many_field(Node, nodes)

    def validate_apply_assets(self, assets):
        return self.filter_many_to_many_field(Asset, assets)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.is_final_approval and (
                not attrs.get('apply_nodes') and not attrs.get('apply_assets')
        ):
            raise serializers.ValidationError({
                'apply_nodes': asset_or_node_help_text,
                'apply_assets': asset_or_node_help_text,
            })

        return attrs


class ApproveAssetSerializer(ApplyAssetSerializer):
    class Meta(ApplyAssetSerializer.Meta):
        read_only_fields = ApplyAssetSerializer.Meta.read_only_fields + ['title', 'type']


class ApplyAssetDisplaySerializer(ApplyAssetSerializer):
    apply_nodes = serializers.SerializerMethodField()
    apply_assets = serializers.SerializerMethodField()
    apply_system_users = serializers.SerializerMethodField()

    class Meta:
        model = ApplyAssetSerializer.Meta.model
        fields = ApplyAssetSerializer.Meta.fields
        read_only_fields = fields

    @staticmethod
    def get_apply_nodes(instance):
        with tmp_to_org(instance.org_id):
            return instance.apply_nodes.values_list('id', flat=True)

    @staticmethod
    def get_apply_assets(instance):
        with tmp_to_org(instance.org_id):
            return instance.apply_assets.values_list('id', flat=True)

    @staticmethod
    def get_apply_system_users(instance):
        with tmp_to_org(instance.org_id):
            return instance.apply_system_users.values_list('id', flat=True)
