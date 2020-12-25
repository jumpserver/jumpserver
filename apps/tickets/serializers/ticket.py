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
            'org_id', 'org_name',
            'body'
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

    @property
    def view_action(self):
        view_action = self.context['view'].action
        return view_action

    @property
    def view_action_is_apply(self):
        return self.view_action == const.TicketActionChoices.apply.value

    @property
    def view_action_is_approve(self):
        return self.view_action == const.TicketActionChoices.approve.value

    @property
    def view_action_is_reject(self):
        return self.view_action == const.TicketActionChoices.reject.value

    @property
    def view_action_is_close(self):
        return self.view_action == const.TicketActionChoices.close.value

    def perform_apply_validate(self, attrs):
        applied_attrs = {}
        applicant = self.context['request'].user
        applied_attrs.update(attrs)
        applied_attrs['applicant'] = applicant
        applied_attrs['applicant_display'] = str(applicant)
        return applied_attrs

    def perform_close_validate(self, _=None):
        closed_attrs = {}
        processor = self.context['request'].user
        closed_attrs['processor'] = processor
        closed_attrs['processor_display'] = str(processor)
        closed_attrs['status'] = const.TicketStatusChoices.closed.value
        closed_attrs['action'] = const.TicketActionChoices.close.value
        return closed_attrs

    def perform_approve_validate(self, attrs):
        approved_attrs = {}
        closed_attrs = self.perform_close_validate()
        approved_attrs.update(closed_attrs)
        approved_attrs['meta'] = attrs['meta']
        approved_attrs['action'] = const.TicketActionChoices.approve.value
        return approved_attrs

    def perform_reject_validate(self, attrs):
        rejected_attrs = {}
        closed_attrs = self.perform_close_validate()
        rejected_attrs.update(closed_attrs)
        rejected_attrs['action'] = const.TicketActionChoices.reject.value
        return rejected_attrs

    def validate(self, attrs):
        perform_view_action_validate_method = getattr(self, f'perform_{self.view_action}_validate')
        if perform_view_action_validate_method:
            attrs = perform_view_action_validate_method(attrs)
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
