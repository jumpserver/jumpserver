# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from orgs.models import Organization
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from tickets.models import Ticket, TicketFlow

__all__ = [
    'TicketDisplaySerializer', 'TicketApplySerializer'
]


class TicketSerializer(OrgResourceModelSerializerMixin):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    status_display = serializers.ReadOnlyField(source='get_status_display', label=_('Status display'))

    class Meta:
        model = Ticket
        fields_mini = ['id', 'title']
        fields_small = fields_mini + [
            'type', 'type_display', 'status', 'status_display',
            'state', 'approval_step', 'rel_snapshot', 'comment',
            'date_created', 'date_updated', 'org_id', 'rel_snapshot',
            'process_map', 'org_name', 'serial_num'
        ]
        fields_fk = ['applicant', ]
        fields = fields_small + fields_fk


class TicketDisplaySerializer(TicketSerializer):
    class Meta:
        model = Ticket
        fields = TicketSerializer.Meta.fields
        read_only_fields = fields


class TicketApplySerializer(TicketSerializer):
    org_id = serializers.CharField(
        required=True, max_length=36, allow_blank=True, label=_("Organization")
    )

    class Meta:
        model = Ticket
        fields = TicketSerializer.Meta.fields
        extra_kwargs = {
            'type': {'required': True}
        }

    @staticmethod
    def validate_org_id(org_id):
        org = Organization.get_instance(org_id)
        if not org:
            error = _('The organization `{}` does not exist'.format(org_id))
            raise serializers.ValidationError(error)
        return org_id

    def validate(self, attrs):
        ticket_type = attrs.get('type')
        org_id = attrs.get('org_id')
        flow = TicketFlow.get_org_related_flows(org_id=org_id).filter(type=ticket_type).first()
        if flow:
            attrs['flow'] = flow
        else:
            error = _('The ticket flow `{}` does not exist'.format(ticket_type))
            raise serializers.ValidationError(error)
        return attrs
