from rest_framework import serializers

from common.drf.serializers import BulkModelSerializer, AdaptedBulkListSerializer
from ..models import (
    Terminal, Status, Session, Task
)


class TerminalSerializer(BulkModelSerializer):
    session_online = serializers.SerializerMethodField()
    is_alive = serializers.BooleanField(read_only=True)

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'http_port', 'ssh_port',
            'comment', 'is_accepted', "is_active", 'session_online',
            'is_alive', 'date_created', 'command_storage', 'replay_storage'
        ]

    @staticmethod
    def get_session_online(obj):
        return Session.objects.filter(terminal=obj, is_finished=False).count()


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'terminal']
        model = Status


class TaskSerializer(BulkModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = AdaptedBulkListSerializer
