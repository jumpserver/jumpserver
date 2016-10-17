# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from .models import Terminal


class TerminalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terminal
        fields = ['name', 'ip', 'type', 'url', 'comment', 'is_active', 'is_accepted',
                  'get_type_display']


if __name__ == '__main__':
    pass
