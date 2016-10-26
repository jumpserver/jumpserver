# -*- coding: utf-8 -*-
#
from __future__ import absolute_import, unicode_literals
from rest_framework import serializers

from common.utils import timesince
from . import models


class ProxyLogSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()
    command_length = serializers.SerializerMethodField()

    class Meta:
        model = models.ProxyLog
        fields = ['id', 'name', 'username', 'hostname', 'ip', 'system_user', 'login_type', 'terminal',
                  'log_file', 'was_failed', 'is_finished', 'date_start', 'time', 'command_length', "commands_dict"]

    @staticmethod
    def get_time(obj):
        return timesince(obj.date_start, since=obj.date_finished)

    @staticmethod
    def get_command_length(obj):
        return len(obj.command_log.all())


class CommandLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CommandLog
