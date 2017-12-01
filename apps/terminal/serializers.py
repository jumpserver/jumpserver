# -*- coding: utf-8 -*-
#

from django.utils import timezone
from rest_framework import serializers

from .models import Terminal, Status, Session, Task
from .hands import ProxyLog


class TerminalSerializer(serializers.ModelSerializer):
    session_online = serializers.SerializerMethodField()
    is_alive = serializers.SerializerMethodField()

    class Meta:
        model = Terminal
        fields = ['id', 'name', 'remote_addr', 'http_port', 'ssh_port',
                  'comment', 'is_accepted', 'session_online', 'is_alive']

    @staticmethod
    def get_session_online(obj):
        return Session.objects.filter(terminal=obj.id, is_finished=False).count()

    @staticmethod
    def get_is_alive(obj):
        status = obj.status_set.latest()

        if not status:
            return False

        delta = timezone.now() - status.date_created
        if delta < timezone.timedelta(seconds=600):
            return True
        else:
            return False


class TerminalSessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Session
        fields = '__all__'


class TerminalStatusSerializer(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Status


class TerminalTaskSerializer(serializers.ModelSerializer):

    class Meta:
        fields = '__all__'
        model = Task
