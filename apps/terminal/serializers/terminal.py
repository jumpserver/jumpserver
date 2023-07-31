from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers import BulkModelSerializer
from common.serializers.fields import LabeledChoiceField
from common.utils import get_request_ip, pretty_string, is_uuid
from users.serializers import ServiceAccountSerializer
from .. import const
from ..models import Terminal, Status, Task, CommandStorage, ReplayStorage


class StatSerializer(serializers.ModelSerializer):
    sessions = serializers.ListSerializer(
        child=serializers.CharField(max_length=36),
        write_only=True
    )

    class Meta:
        model = Status
        fields_mini = ['id']
        fields_write_only = ['sessions', ]
        fields_small = fields_mini + fields_write_only + [
            'cpu_load', 'memory_used', 'disk_used',
            'session_online', 'date_created'
        ]
        fields_fk = ['terminal']
        fields = fields_small + fields_fk
        extra_kwargs = {
            "cpu_load": {'default': 0},
            "memory_used": {'default': 0},
            "disk_used": {'default': 0},
        }


class TerminalSmallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terminal
        fields = ['id', 'name', 'type']


class TerminalSerializer(BulkModelSerializer):
    session_online = serializers.ReadOnlyField(source='get_online_session_count')
    is_alive = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True, label='Is active')
    load = LabeledChoiceField(
        read_only=True, choices=const.ComponentLoad.choices,
        label=_('Load status')
    )
    stat = StatSerializer(read_only=True, source='last_stat')

    class Meta:
        model = Terminal
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'type', 'remote_addr', 'session_online',
            'command_storage', 'replay_storage',
            'is_active', 'is_alive',
            'date_created', 'comment',
        ]
        fields_fk = ['load', 'stat']
        fields = fields_small + fields_fk
        read_only_fields = ['type', 'date_created']
        extra_kwargs = {
            'command_storage': {'required': True, },
            'replay_storage': {'required': True, },
        }

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


class TaskSerializer(BulkModelSerializer):
    class Meta:
        fields = '__all__'
        model = Task
        ref_name = 'TerminalTaskSerializer'


class TerminalRegistrationSerializer(serializers.ModelSerializer):
    service_account = ServiceAccountSerializer(read_only=True)

    class Meta:
        model = Terminal
        fields = ['name', 'type', 'comment', 'service_account', 'remote_addr']
        extra_kwargs = {
            'name': {'max_length': 1024},
            'remote_addr': {'read_only': True}
        }

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=raise_exception)
        if not valid:
            return valid
        raw_name = self.validated_data.get('name')
        name = pretty_string(raw_name)
        self.validated_data['name'] = name
        if len(raw_name) > 128:
            self.validated_data['comment'] = raw_name
        data = {'name': name}
        kwargs = {'data': data}
        if self.instance and self.instance.user:
            kwargs['instance'] = self.instance.user
        self.service_account = ServiceAccountSerializer(**kwargs)
        valid = self.service_account.is_valid(raise_exception=True)
        return valid

    def create(self, validated_data):
        instance = super().create(validated_data)
        request = self.context.get('request')
        instance.is_accepted = True
        if request:
            instance.remote_addr = get_request_ip(request)
        sa = self.service_account.create(validated_data)
        sa.system_roles.add_role_system_component()
        instance.user = sa
        instance.command_storage = CommandStorage.default().name
        instance.replay_storage = ReplayStorage.default().name
        instance.save()
        return instance


class ConnectMethodSerializer(serializers.Serializer):
    value = serializers.CharField(max_length=128)
    label = serializers.CharField(max_length=128)
    type = serializers.CharField(max_length=128)
    endpoint_protocol = serializers.CharField(max_length=128)
    component = serializers.CharField(max_length=128)
