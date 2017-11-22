# -*- coding: utf-8 -*-
#

from django.utils import timezone
from rest_framework import serializers

from .models import Terminal, TerminalStatus, TerminalSession, TerminalTask
from .hands import ProxyLog


class TerminalSerializer(serializers.ModelSerializer):
    session_connected = serializers.SerializerMethodField()
    is_alive = serializers.SerializerMethodField()

    class Meta:
        model = Terminal
        fields = ['id', 'name', 'remote_addr', 'http_port', 'ssh_port',
                  'comment', 'is_accepted', 'session_connected', 'is_alive']

    @staticmethod
    def get_session_connected(obj):
        return TerminalSession.objects.filter(terminal=obj.id, is_finished=False)

    @staticmethod
    def get_is_alive(obj):
        log = obj.terminalstatus_set.last()
        if log and timezone.now() - log.date_created < timezone.timedelta(seconds=600):
            return True
        else:
            return False


class TerminalSessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = TerminalSession
        fields = '__all__'


class TerminalStatusSerializer(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = TerminalStatus


class TerminalTaskSerializer(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = TerminalTask
