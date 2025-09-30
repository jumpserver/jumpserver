from common.api import JMSBulkModelViewSet
from terminal import serializers
from terminal.filters import ChatFilter
from terminal.models import Chat

__all__ = ['ChatViewSet']


class ChatViewSet(JMSBulkModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = serializers.ChatSerializer
    filterset_class = ChatFilter
    search_fields = ['title']
    ordering_fields = ['date_updated']
    ordering = ['-date_updated']
