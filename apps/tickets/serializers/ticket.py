# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from ..models import Ticket, Comment

__all__ = ['TicketSerializer', 'CommentSerializer']


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'type', 'type_display', 'meta', 'action', 'action_display', 'status',
            'applicant', 'applicant_display',
            'approver', 'approver_display',
            'assignees', 'assignees_display',
            'date_created', 'date_updated',
        ]
        read_only_fields = [
            'applicant', 'approver',
            'applicant_display', 'approver_display', 'assignees_display',
            'date_created', 'date_updated',
        ]


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
