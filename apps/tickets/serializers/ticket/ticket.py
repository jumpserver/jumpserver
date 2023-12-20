# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from orgs.models import Organization
from tickets.const import TicketType, TicketStatus, TicketState
from tickets.models import Ticket, TicketFlow
from users.models import User

__all__ = [
    'TicketApplySerializer', 'TicketApproveSerializer', 'TicketSerializer',
]


class TicketSerializer(OrgResourceModelSerializerMixin):
    type = LabeledChoiceField(choices=TicketType.choices, read_only=True, label=_('Type'))
    status = LabeledChoiceField(choices=TicketStatus.choices, read_only=True, label=_('Status'))
    state = LabeledChoiceField(choices=TicketState.choices, read_only=True, label=_("State"))

    class Meta:
        model = Ticket
        fields_mini = ['id', 'title']
        fields_small = fields_mini + ['org_id', 'comment']
        read_only_fields = [
            'serial_num', 'process_map', 'approval_step', 'type', 'state', 'applicant',
            'status', 'date_created', 'date_updated', 'org_name', 'rel_snapshot'
        ]
        fields = fields_small + read_only_fields
        extra_kwargs = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_type_choices()

    def set_type_choices(self):
        tp = self.fields.get('type')
        if not tp:
            return
        choices = tp.choices
        choices.pop(TicketType.general, None)
        tp.choices = choices.items()

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related('ticket_steps')
        return queryset


class TicketApproveSerializer(TicketSerializer):
    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields
        read_only_fields = fields


class TicketApplySerializer(TicketSerializer):
    org_id = serializers.CharField(
        required=True, max_length=36, allow_blank=True, label=_("Organization")
    )
    applicant = serializers.CharField(required=False, allow_blank=True)

    def get_applicant(self, applicant_id):
        current_user = self.context['request'].user
        want_applicant = User.objects.filter(id=applicant_id).first()
        if want_applicant and current_user.has_perm('tickets.add_superticket'):
            applicant = want_applicant
        else:
            applicant = current_user
        return applicant

    @staticmethod
    def validate_org_id(org_id):
        org = Organization.get_instance(org_id)
        if not org:
            error = _('The organization `{}` does not exist'.format(org_id))
            raise serializers.ValidationError(error)
        return org_id

    def validate(self, attrs):
        if self.instance:
            return attrs

        ticket_type = attrs.get('type')
        org_id = attrs.get('org_id')
        flow = TicketFlow.get_org_related_flows(org_id=org_id).filter(type=ticket_type).first()
        if not flow:
            error = _('The ticket flow `{}` does not exist'.format(ticket_type))
            raise serializers.ValidationError(error)
        attrs['flow'] = flow
        attrs['applicant'] = self.get_applicant(attrs.get('applicant'))
        return attrs
