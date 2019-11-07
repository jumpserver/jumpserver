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
            'status', 'date_created', 'date_updated',
        ]
        read_only_fields = [
            'user_display', 'assignees_display',
            'date_created', 'date_updated',
        ]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Comment
        fields = [
            'id', 'ticket', 'body', 'user', 'user_display',
            'date_created', 'date_updated'
        ]
        read_only_fields = [
            'user_display', 'date_created', 'date_updated'
        ]
