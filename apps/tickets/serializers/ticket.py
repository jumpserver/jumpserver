# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from ..models import Ticket, Comment
from .. import const

__all__ = ['TicketSerializer', 'CommentSerializer']


class TicketSerializer(serializers.ModelSerializer):
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type'))
    status_display = serializers.ReadOnlyField(source='get_status_display', label=_('Status'))
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_('Action'))

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'type', 'type_display',
            'meta', 'action', 'action_display', 'status',
            'applicant', 'applicant_display',
            'processor', 'processor_display',
            'assignees', 'assignees_display',
            'date_created', 'date_updated',
            'org_id', 'org_name'
        ]
        read_only_fields = [
            'applicant', 'applicant_display',
            'processor', 'processor_display',
            'assignees_display',
            'date_created', 'date_updated', 'org_name'
        ]
        extra_kwargs = {
            'title': {'required': False},
            'assignees': {'required': False}
        }

    def perform_apply_validate(self, attrs):
        applied_attrs = {}
        applicant = self.context['request'].user
        applied_attrs['applicant'] = applicant
        applied_attrs['applicant_display'] = str(applicant)
        return attrs

    def perform_close_validate(self):
        closed_attrs = {}
        processor = self.context['request'].user
        closed_attrs['processor'] = processor
        closed_attrs['processor_display'] = str(processor)
        closed_attrs['status'] = const.TicketStatusChoices.closed.value
        return closed_attrs

    def perform_approve_validate(self, attrs):
        approved_attrs = {}
        closed_attrs = self.perform_close_validate()
        approved_attrs['meta'] = attrs['meta']
        approved_attrs.update(closed_attrs)
        approved_attrs['action'] = const.TicketActionChoices.approve.value
        return attrs

    def perform_reject_validate(self, attrs):
        rejected_attrs = {}
        closed_attrs = self.perform_close_validate()
        rejected_attrs.update(closed_attrs)
        rejected_attrs['action'] = const.TicketActionChoices.reject.value
        return attrs

    def validate(self, attrs):
        view_action = self.context['view'].action
        if view_action == 'apply':
            attrs = self.perform_apply_validate(attrs)
        elif view_action == 'approve':
            attrs = self.perform_approve_validate(attrs)
        elif view_action == 'reject':
            attrs = self.perform_reject_validate(attrs)
        elif view_action == 'close':
            attrs = self.perform_close_validate()
        else:
            attrs = {}
        return attrs

    def update(self, instance, validated_data):
        meta = instance.meta
        new_meta = validated_data['meta']
        meta.update(new_meta)
        validated_data['meta'] = meta
        return super().update(instance, validated_data)


class CurrentTicket(object):
    ticket = None

    def set_context(self, serializer_field):
        self.ticket = serializer_field.context['ticket']

    def __call__(self):
        return self.ticket


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault(),
    )
    ticket = serializers.HiddenField(
        default=CurrentTicket()
    )

    class Meta:
        model = Comment
        fields = [
            'id', 'ticket', 'body', 'user', 'user_display',
            'date_created', 'date_updated'
        ]
        read_only_fields = [
            'user_display', 'date_created', 'date_updated'
        ]
