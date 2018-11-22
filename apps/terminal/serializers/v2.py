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

    def validate_name(self, value):
        request = self.context.get('request')
        if request and not hasattr(request.user, 'terminal'):
            return value
        else:
            raise serializers.ValidationError("This user already have terminal")
