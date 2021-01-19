# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from common.drf.serializers import MethodSerializer
from orgs.utils import get_org_by_id
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from users.models import User
from tickets.models import Ticket
from .meta import type_serializer_classes_mapping


__all__ = [
    'TicketDisplaySerializer', 'TicketApplySerializer', 'TicketApproveSerializer',
]


class TicketSerializer(OrgResourceModelSerializerMixin):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    action_display = serializers.ReadOnlyField(
        source='get_action_display', label=_('Action display')
    )
    status_display = serializers.ReadOnlyField(
        source='get_status_display', label=_('Status display')
    )
    meta = MethodSerializer()

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'type', 'type_display',
            'meta', 'action', 'action_display', 'status', 'status_display',
            'applicant', 'applicant_display', 'processor', 'processor_display',
            'assignees', 'assignees_display', 'comment',
            'date_created', 'date_updated',
            'org_id', 'org_name',
            'body'
        ]

    def get_meta_serializer(self):
        default_serializer = serializers.Serializer(read_only=True)
        if isinstance(self.instance, Ticket):
            _type = self.instance.type
        else:
            _type = self.context['request'].query_params.get('type')

        if _type:
            action_serializer_classes_mapping = type_serializer_classes_mapping.get(_type)
            if action_serializer_classes_mapping:
                query_action = self.context['request'].query_params.get('action')
                action = query_action if query_action else self.context['view'].action
                serializer_class = action_serializer_classes_mapping.get(action)
                if not serializer_class:
                    serializer_class = action_serializer_classes_mapping.get('default')
            else:
                serializer_class = default_serializer
        else:
            serializer_class = default_serializer

        if not serializer_class:
            serializer_class = default_serializer

        if isinstance(serializer_class, type):
            serializer = serializer_class()
        else:
            serializer = serializer_class

        return serializer


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
        writeable_fields = [
            'id', 'title', 'type', 'meta', 'assignees', 'comment', 'org_id'
        ]
        read_only_fields = list(set(fields) - set(writeable_fields))
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


class TicketApproveSerializer(TicketSerializer):

    class Meta:
        model = Ticket
        fields = TicketSerializer.Meta.fields
        writeable_fields = ['meta']
        read_only_fields = list(set(fields) - set(writeable_fields))

    def validate_meta(self, meta):
        _meta = self.instance.meta if self.instance else {}
        _meta.update(meta)
        return _meta
