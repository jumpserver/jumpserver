# -*- coding: utf-8 -*-
#

from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkSerializerMixin
from .models import Terminal, Status, Session, Task
from .backends import get_multi_command_storage


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
        key = StatusSerializer.CACHE_KEY_PREFIX + str(obj.id)
        return cache.get(key)


class SessionSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    command_amount = serializers.SerializerMethodField()
    command_store = get_multi_command_storage()

    class Meta:
        model = Session
        list_serializer_class = BulkListSerializer
        fields = '__all__'

    def get_command_amount(self, obj):
        return self.command_store.count(session=str(obj.id))


class StatusSerializer(serializers.ModelSerializer):
    CACHE_KEY_PREFIX = 'terminal_status_'

    class Meta:
        fields = '__all__'
        model = Status

    def create(self, validated_data):
        terminal_id = str(validated_data['terminal'].id)
        key = self.CACHE_KEY_PREFIX + terminal_id
        cache.set(key, 1, 60)
        return validated_data


class TaskSerializer(BulkSerializerMixin, serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
        list_serializer_class = BulkListSerializer


class ReplaySerializer(serializers.Serializer):
    file = serializers.FileField()

