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
        fields = '__all__'

    @staticmethod
    def get_time(obj):
        if not obj.is_finished:
            return ''
        else:
            return timesince(obj.date_start, since=obj.date_finished)

    @staticmethod
    def get_command_length(obj):
        return 2

