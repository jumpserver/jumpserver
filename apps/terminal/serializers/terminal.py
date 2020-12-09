from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.drf.serializers import BulkModelSerializer, AdaptedBulkListSerializer
from common.drf.fields import CharPrimaryKeyRelatedField
from common.utils import is_uuid
from ..models import (
    Terminal, Session, Task, CommandStorage, ReplayStorage
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


class StatusSerializer(serializers.Serializer):
    # terminal
    TERMINAL_TYPE_CHOICES = (
        ('core', 'Core'),
        ('koko', 'KoKo'),
        ('guacamole', 'Guacamole'),
        ('omnidb', 'OmniDB')
    )
    terminal_id = CharPrimaryKeyRelatedField(
        queryset=Terminal.objects, required=True, label=_("Terminal ID")
    )
    terminal_name = serializers.CharField(
        max_length=128, required=True, label=_("Terminal name")
    )
    terminal_type = serializers.ChoiceField(
        required=True, choices=TERMINAL_TYPE_CHOICES
    )
    terminal_is_alive = serializers.BooleanField(
        read_only=True, default=True, label=_("Alive")
    )
    # system
    system_cpu_load_1 = serializers.FloatField(
        required=True, label=_("System cpu load 1 minutes")
    )
    system_cpu_load_5 = serializers.FloatField(
        required=True, label=_("System cpu load 5 minutes")
    )
    system_cpu_load_15 = serializers.FloatField(
        required=True, label=_("System cpu load 15 minutes")
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


class TaskSerializer(BulkModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = AdaptedBulkListSerializer
