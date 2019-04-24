# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.mixins import BulkSerializerMixin
from common.serializers import AdaptedBulkListSerializer
from ..models import Terminal, Status, Session, Task


class TerminalSerializer(serializers.ModelSerializer):
    session_online = serializers.SerializerMethodField()
    is_alive = serializers.BooleanField(read_only=True)

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'http_port', 'ssh_port',
            'comment', 'is_accepted', "is_active", 'session_online',
            'is_alive'
        ]

    @staticmethod
    def get_session_online(obj):
        return Session.objects.filter(terminal=obj, is_finished=False).count()


class SessionSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    command_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = Session
        list_serializer_class = AdaptedBulkListSerializer
        fields = '__all__'


class StatusSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ['id', 'terminal']
        model = Status


class TaskSerializer(BulkSerializerMixin, serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = AdaptedBulkListSerializer


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)


