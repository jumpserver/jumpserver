# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from orgs.utils import get_org_by_id
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from users.models import User
from ..models import Ticket
from .. import const

__all__ = [
    'TicketSerializer', 'TicketDisplaySerializer',
    'TicketApplySerializer', 'TicketApproveSerializer',
    'TicketRejectSerializer', 'TicketCloseSerializer',
]


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'type',
            'meta', 'action', 'status',
            'applicant', 'applicant_display',
            'processor', 'processor_display',
            'assignees', 'assignees_display',
            'date_created', 'date_updated',
            'org_id', 'org_name',
            'body'
        ]


class TicketDisplaySerializer(OrgResourceModelSerializerMixin):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type'))
    status_display = serializers.ReadOnlyField(source='get_status_display', label=_('Status'))
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_('Action'))

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ['type_display', 'status_display', 'action_display']


class TicketActionSerializer(TicketSerializer):

    class Meta(TicketSerializer.Meta):
        fields = ['action']
        extra_kwargs = {
            'action': {'default': const.TicketActionChoices.apply.value}
        }


class TicketApplySerializer(TicketActionSerializer):
    org_id = serializers.CharField(
        max_length=36, allow_blank=True, required=True, label=_("Organization")
    )
    applicant = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta(TicketActionSerializer.Meta):
        fields = TicketActionSerializer.Meta.fields + [
            'id', 'title', 'type', 'applicant', 'meta', 'assignees', 'org_id'
        ]
        extra_kwargs = {
            'type': {'required': True}
        }

    @staticmethod
    def validate_org_id(org_id):
        org = get_org_by_id(org_id)
        if not org:
            error = _('The organization `{}` does not exist'.format(org_id))
            raise serializers.ValidationError(error)
        return org_id

    def validate_assignees(self, assignees):
        org_id = self.initial_data.get('org_id')
        self.validate_org_id(org_id)
        org = get_org_by_id(org_id)
        admins = User.get_super_and_org_admins(org)
        invalid_assignees = set(assignees) - set(admins)
        if invalid_assignees:
            invalid_assignees_display = [str(assignee) for assignee in invalid_assignees]
            error = _('Assignees `{}` are not super admin or organization `{}` admin'
                      ''.format(invalid_assignees_display, org.name))
            raise serializers.ValidationError(error)
        return assignees

    @staticmethod
    def validate_action():
        return const.TicketActionChoices.apply.value


class TicketProcessSerializer(TicketActionSerializer):
    processor = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta(TicketActionSerializer.Meta):
        fields = TicketActionSerializer.Meta.fields + ['processor']


class TicketApproveSerializer(TicketProcessSerializer):

    class Meta(TicketProcessSerializer.Meta):
        fields = TicketProcessSerializer.Meta.fields + ['meta']

    def validate_meta(self, meta):
        meta.update(self.instance.meta)
        return meta

    @staticmethod
    def validate_action(action):
        return const.TicketActionChoices.approve.value


class TicketRejectSerializer(TicketProcessSerializer):

    @staticmethod
    def validate_action(action):
        return const.TicketActionChoices.reject.value


class TicketCloseSerializer(TicketProcessSerializer):

    @staticmethod
    def validate_action(action):
        return const.TicketActionChoices.close.value


