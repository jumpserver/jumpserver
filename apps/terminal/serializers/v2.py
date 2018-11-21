# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from ..models import Terminal


class TerminalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'comment',
        ]
        read_only_fields = ['id']
