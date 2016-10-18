# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from .models import Terminal, TerminalHeatbeat


class TerminalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terminal
        fields = ['name', 'ip', 'type', 'url', 'comment', 'is_active', 'is_accepted',
                  'get_type_display']


class TerminalHeatbeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = TerminalHeatbeat
        fields = ['terminal']


if __name__ == '__main__':
    pass
