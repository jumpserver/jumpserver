# -*- coding: utf-8 -*-
#

from django.utils import timezone
from rest_framework import serializers
from rest_framework_bulk.serializers import BulkListSerializer


from common.mixins import BulkSerializerMixin
from common.utils import get_object_or_none
from .models import Terminal, Status, Session, Task
from .backends import get_multi_command_store


class TerminalSerializer(serializers.ModelSerializer):
    session_online = serializers.SerializerMethodField()
    is_alive = serializers.SerializerMethodField()

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'http_port', 'ssh_port',
            'comment', 'is_accepted', "is_active", 'session_online',
            'is_alive'
        ]

    @staticmethod
    def get_session_online(obj):
        return Session.objects.filter(terminal=obj.id, is_finished=False).count()

    @staticmethod
    def get_is_alive(obj):
        try:
            status = obj.status_set.latest()
        except Status.DoesNotExist:
            status = None

        if not status:
            return False

        delta = timezone.now() - status.date_created
        if delta < timezone.timedelta(seconds=600):
            return True
        else:
            return False


class SessionSerializer(serializers.ModelSerializer):
    command_amount = serializers.SerializerMethodField()
    command_store = get_multi_command_store()

    class Meta:
        model = Session
        list_serializer_class = BulkListSerializer
        fields = '__all__'

    def get_command_amount(self, obj):
        return self.command_store.count(session=str(obj.id))


class StatusSerializer(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Status


class TaskSerializer(BulkSerializerMixin, serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = BulkListSerializer


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField()

