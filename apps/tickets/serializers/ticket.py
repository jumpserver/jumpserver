# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from orgs.utils import get_org_by_id
from users.models import User
from ..models import Ticket, Comment
from .. import const

__all__ = ['TicketSerializer', 'AssigneeSerializer', 'CommentSerializer']


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
            'date_created', 'date_updated',
            'org_name'
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

    def validate_assignees(self, assignees):
        if not self.view_action_is_apply:
            return assignees
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

    def validate_org_id(self, org_id):
        if not self.view_action_is_apply:
            return org_id
        if org_id is None:
            error = _('`org_id` field is required')
            raise serializers.ValidationError(error)
        org = get_org_by_id(org_id)
        if not org:
            error = _('The organization `{}` does not exist'.format(org_id))
            raise serializers.ValidationError(error)
        return org_id

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
        perform_validate_method = getattr(self, f'perform_{self.view_action}_validate', None)
        if perform_validate_method:
            attrs = perform_validate_method(attrs)
        else:
            attrs = {}
        return attrs

    def update(self, instance, validated_data):
        new_meta = validated_data.get('meta')
        if new_meta:
            meta = instance.meta
            meta.update(new_meta)
            validated_data['meta'] = meta
        return super().update(instance, validated_data)


class AssigneeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    username = serializers.CharField()


class CurrentTicket(object):
    ticket = None

    def set_context(self, serializer_field):
        self.ticket = serializer_field.context['ticket']

    def __call__(self):
        return self.ticket


class CommentSerializer(serializers.ModelSerializer):
    ticket = serializers.HiddenField(default=CurrentTicket())
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Comment
        fields = [
            'id', 'ticket', 'body', 'user', 'user_display', 'date_created', 'date_updated'
        ]
        read_only_fields = [
            'user_display', 'date_created', 'date_updated'
        ]
