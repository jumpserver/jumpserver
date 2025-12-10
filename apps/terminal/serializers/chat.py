from rest_framework import serializers

from common.serializers import CommonBulkModelSerializer
from terminal.models import Chat

__all__ = ['ChatSerializer']


class ChatSerializer(CommonBulkModelSerializer):
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields_mini = ['id', 'title', 'created_at', 'updated_at']
        fields = fields_mini + [
            'chat', 'meta', 'pinned', 'archived',
            'share_id', 'folder_id',
            'user_id', 'session_info'
        ]

    @staticmethod
    def get_created_at(obj):
        return int(obj.date_created.timestamp())

    @staticmethod
    def get_updated_at(obj):
        return int(obj.date_updated.timestamp())
