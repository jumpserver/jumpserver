from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.drf.serializers import BulkModelSerializer, AdaptedBulkListSerializer
from common.utils import is_uuid
from users.serializers import ServiceAccountSerializer
from common.utils import get_request_ip

from ..models import (
    Terminal, Status, Session, Task, CommandStorage, ReplayStorage
)
from .components import ComponentsStateSerializer


class TerminalSerializer(BulkModelSerializer):
    session_online = serializers.SerializerMethodField()
    is_alive = serializers.BooleanField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(read_only=True)
    state = ComponentsStateSerializer(read_only=True)

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'type', 'remote_addr', 'http_port', 'ssh_port',
            'comment', 'is_accepted', "is_active", 'session_online',
            'is_alive', 'date_created', 'command_storage', 'replay_storage',
            'status', 'status_display', 'state'
        ]
        read_only_fields = ['type', 'date_created']

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


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'terminal']
        model = Status


class TaskSerializer(BulkModelSerializer):
    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = AdaptedBulkListSerializer
        ref_name = 'TerminalTaskSerializer'


class TerminalRegistrationSerializer(serializers.ModelSerializer):
    service_account = ServiceAccountSerializer(read_only=True)

    class Meta:
        model = Terminal
        fields = ['name', 'type', 'comment', 'service_account', 'remote_addr']
        extra_fields = {
            'remote_addr': {'readonly': True}
        }

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=raise_exception)
        if not valid:
            return valid
        data = {'name': self.validated_data.get('name')}
        kwargs = {'data': data}
        if self.instance and self.instance.user:
            kwargs['instance'] = self.instance.user
        self.service_account = ServiceAccountSerializer(**kwargs)
        valid = self.service_account.is_valid(raise_exception=True)
        return valid

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        request = self.context.get('request')
        instance.is_accepted = True
        if request:
            instance.remote_addr = get_request_ip(request)
        sa = self.service_account.save()
        instance.user = sa
        instance.save()
        return instance
