# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from .. import models

__all__ = ['TicketSerializer', 'CommentSerializer']


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Ticket
        fields = [
            'id', 'user', 'user_display', 'title', 'body',
            'assignees', 'assignees_display',
            'status', 'action', 'date_created', 'date_updated',
            'type', 'type_display', 'action_display',
        ]
        read_only_fields = [
            'user_display', 'assignees_display',
            'date_created', 'date_updated',
        ]

    def create(self, validated_data):
        validated_data.pop('action')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        action = validated_data.get("action")
        user = self.context["request"].user

        if action and user not in instance.assignees.all():
            error = {"action": "Only assignees can update"}
            raise serializers.ValidationError(error)
        if instance.status == instance.STATUS_CLOSED:
            validated_data.pop('action')
        instance = super().update(instance, validated_data)
        if not instance.status == instance.STATUS_CLOSED and action:
            instance.perform_action(action, user)
        return instance


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
        model = models.Comment
        fields = [
            'id', 'ticket', 'body', 'user', 'user_display',
            'date_created', 'date_updated'
        ]
        read_only_fields = [
            'user_display', 'date_created', 'date_updated'
        ]
