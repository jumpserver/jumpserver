# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from common.drf.fields import ReadableHiddenField
from common.drf.serializers import DynamicMappingSerializer
from orgs.utils import get_org_by_id
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from users.models import User
from tickets import const
from tickets.models import Ticket
from .meta import meta_field_dynamic_mapping_serializers

__all__ = [
    'TicketSerializer', 'TicketDisplaySerializer',
    'TicketApplySerializer', 'TicketApproveSerializer',
    'TicketRejectSerializer', 'TicketCloseSerializer',
]


class TicketSerializer(OrgResourceModelSerializerMixin):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type'))
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_('Action'))
    status_display = serializers.ReadOnlyField(source='get_status_display', label=_('Status'))
    meta = DynamicMappingSerializer(mapping_serializers=meta_field_dynamic_mapping_serializers)

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'type', 'type_display',
            'meta', 'action', 'action_display', 'status', 'status_display',
            'applicant', 'applicant_display', 'processor', 'processor_display',
            'assignees', 'assignees_display',
            'date_created', 'date_updated',
            'org_id', 'org_name',
            'body'
        ]

    def get_meta_mapping_rule(self, mapping_serializers):
        view = self.context['view']
        request = self.context['request']
        query_type = request.query_params.get('type')
        query_action = request.query_params.get('action')
        action = query_action if query_action else view.action
        mapping_rule = ['type', query_type, action]
        return mapping_rule


class TicketDisplaySerializer(TicketSerializer):

    class Meta(TicketSerializer.Meta):
        read_only_fields = TicketSerializer.Meta.fields


class TicketActionSerializer(TicketSerializer):
    action = ReadableHiddenField(default=const.TicketActionChoices.open.value)

    class Meta(TicketSerializer.Meta):
        required_fields = ['action']
        read_only_fields = list(set(TicketDisplaySerializer.Meta.fields) - set(required_fields))


class TicketApplySerializer(TicketActionSerializer):
    applicant = ReadableHiddenField(default=serializers.CurrentUserDefault())
    org_id = serializers.CharField(
        max_length=36, allow_blank=True, required=True, label=_("Organization")
    )

    class Meta(TicketActionSerializer.Meta):
        required_fields = TicketActionSerializer.Meta.required_fields + [
            'id', 'title', 'type', 'applicant', 'meta', 'assignees', 'org_id'
        ]
        read_only_fields = list(set(TicketDisplaySerializer.Meta.fields) - set(required_fields))
        extra_kwargs = {
            'type': {'required': True},
        }

    def validate_type(self, tp):
        request_type = self.context['request'].query_params.get('type')
        if tp != request_type:
            error = _(
                'The `type` in the submission data (`{}`) is different from the type '
                'in the request url (`{}`)'.format(tp, request_type)
            )
            raise serializers.ValidationError(error)
        return tp

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
        valid_assignees = list(set(assignees) & set(admins))
        if not valid_assignees:
            error = _('None of the assignees belong to Organization `{}` admins'.format(org.name))
            raise serializers.ValidationError(error)
        return valid_assignees

    def validate_action(self, action):
        return const.TicketActionChoices.open.value


class TicketProcessSerializer(TicketActionSerializer):
    processor = ReadableHiddenField(default=serializers.CurrentUserDefault())

    class Meta(TicketActionSerializer.Meta):
        required_fields = TicketActionSerializer.Meta.required_fields + ['processor']
        read_only_fields = list(set(TicketDisplaySerializer.Meta.fields) - set(required_fields))


class TicketApproveSerializer(TicketProcessSerializer):

    class Meta(TicketProcessSerializer.Meta):
        required_fields = TicketProcessSerializer.Meta.required_fields + ['meta']
        read_only_fields = list(set(TicketDisplaySerializer.Meta.fields) - set(required_fields))

    def validate_meta(self, meta):
        instance_meta = self.instance.meta
        instance_meta.update(meta)
        return instance_meta

    @staticmethod
    def validate_action(action):
        return const.TicketActionChoices.approve.value


class TicketRejectSerializer(TicketProcessSerializer):

    def validate_action(self, action):
        return const.TicketActionChoices.reject.value


class TicketCloseSerializer(TicketProcessSerializer):

    def validate_action(self, action):
        return const.TicketActionChoices.close.value


