# -*- coding: utf-8 -*-
#
from __future__ import absolute_import, unicode_literals
from rest_framework import serializers

from . import models


class ProxyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ProxyLog
        fields = ['id', 'name', 'username', 'hostname', 'ip', 'system_user', 'login_type', 'terminal',
                  'log_file', 'was_failed', 'is_finished', 'date_start', 'date_finished', 'get_login_type_display']


class CommandLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CommandLog
