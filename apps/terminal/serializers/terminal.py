from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import TextChoices

from common.drf.serializers import BulkModelSerializer, AdaptedBulkListSerializer
from common.utils import is_uuid
from ..models import (
    Terminal, Session, Task, CommandStorage, ReplayStorage
)


class StateSerializer(serializers.Serializer):
    # system
    system_cpu_load_1 = serializers.FloatField(
        required=True, label=_("System cpu load 1 minutes")
    )
    system_memory_used_percent = serializers.FloatField(
        required=True, label=_('System memory used percent')
    )
    system_disk_used_percent = serializers.FloatField(
        required=True, label=_('System disk used percent')
    )
    # sessions
    sessions_active = serializers.ListField(
        required=False, label=_("Session active")
    )
    session_count_active = serializers.IntegerField(
        required=True, label=_("Session active count")
    )
    session_count_processed = serializers.IntegerField(
        required=True, label=_("Session processed count")
    )
    session_count_failed = serializers.IntegerField(
        required=True, label=_('Session failed count')
    )
    session_count_succeeded = serializers.IntegerField(
        required=True, label=_('Session succeeded count')
    )
    # status
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)


class TerminalSerializer(BulkModelSerializer):
    session_online = serializers.SerializerMethodField()
    is_alive = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True, label=_("Status"))
    state = StateSerializer(read_only=True)

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'http_port', 'ssh_port',
            'comment', 'is_accepted', "is_active", 'session_online',
            'date_created', 'command_storage', 'replay_storage',
            'is_alive', 'status', 'state'
        ]

    @staticmethod
    def get_kwargs_may_be_uuid(value):
        kwargs = {}
        if is_uuid(value):
            kwargs['id'] = value
        else:
            kwargs['name'] = value
        return kwargs

    def validate_command_storage(self, value):
        kwargs = self.get_kwargs_may_be_uuid(value)
        storage = CommandStorage.objects.filter(**kwargs).first()
        if storage:
            return storage.name
        else:
            raise serializers.ValidationError(_('Not found'))

    def validate_replay_storage(self, value):
        kwargs = self.get_kwargs_may_be_uuid(value)
        storage = ReplayStorage.objects.filter(**kwargs).first()
        if storage:
            return storage.name
        else:
            raise serializers.ValidationError(_('Not found'))

    @staticmethod
    def get_session_online(obj):
        return Session.objects.filter(terminal=obj, is_finished=False).count()


class TaskSerializer(BulkModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = AdaptedBulkListSerializer
