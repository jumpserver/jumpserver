# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from .models import Terminal, HeatbeatFailedLog
from .hands import ProxyLog


class TerminalSerializer(serializers.ModelSerializer):
    proxy_online = serializers.SerializerMethodField()

    class Meta:
        model = Terminal
        fields = ['id', 'name', 'ip', 'type', 'url', 'comment',
                  'is_active', 'get_type_display', 'proxy_online']

    @staticmethod
    def get_proxy_online(obj):
        return ProxyLog.objects.filter(terminal=obj.name, is_finished=False).count()


class TerminalHeatbeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeatbeatFailedLog
        fields = ['terminal']


if __name__ == '__main__':
    pass
