from rest_framework import serializers

from common.serializers.fields import ReadableHiddenField
from ..models import Comment

__all__ = ['CommentSerializer']


class CurrentTicket(object):
    ticket = None

    def set_context(self, serializer_field):
        self.ticket = serializer_field.context['ticket']

    def __call__(self):
        return self.ticket


class CommentSerializer(serializers.ModelSerializer):
    ticket = ReadableHiddenField(default=CurrentTicket())
    user = ReadableHiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Comment
        fields_mini = ['id']
        fields_small = fields_mini + [
            'body', 'user_display', 'date_created', 'date_updated'
        ]
        fields_fk = ['ticket', 'user', ]
        fields = fields_small + fields_fk
        read_only_fields = [
            'user_display', 'date_created', 'date_updated'
        ]
