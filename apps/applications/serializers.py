# -*- coding: utf-8 -*-
#

from django.utils import timezone
from rest_framework import serializers

from .models import Terminal, TerminalHeatbeat
from .hands import ProxyLog


class TerminalSerializer(serializers.ModelSerializer):
    session_connected = serializers.SerializerMethodField()
    is_alive = serializers.SerializerMethodField()

    class Meta:
        model = Terminal
        fields = ['id', 'name', 'remote_addr', 'http_port', 'ssh_port',
                  'comment', 'is_accepted',
                  'session_connected', 'is_alive']

    @staticmethod
    def get_session_connected(obj):
        return ProxyLog.objects.filter(terminal=obj.name, is_finished=False).count()

    @staticmethod
    def get_is_alive(obj):
        log = obj.terminalheatbeat_set.last()
        if log and timezone.now() - log.date_created < timezone.timedelta(seconds=600):
            return True
        else:
            return False


class TerminalHeatbeatSerializer(serializers.ModelSerializer):
    date_start = serializers.DateTimeField

    class Meta:
        model = TerminalHeatbeat




