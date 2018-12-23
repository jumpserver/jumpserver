# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.utils import get_request_ip
from users.serializers.v2 import ServiceAccountRegistrationSerializer
from ..models import Terminal


__all__ = ['TerminalSerializer', 'TerminalRegistrationSerializer']


class TerminalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'comment',
        ]
        read_only_fields = ['id', 'remote_addr']


class TerminalRegistrationSerializer(serializers.ModelSerializer):
    service_account = ServiceAccountRegistrationSerializer(read_only=True)
    service_account_serializer = None

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'comment', 'service_account'
        ]
        read_only_fields = ['id', 'remote_addr', 'service_account']

    def validate(self, attrs):
        self.service_account_serializer = ServiceAccountRegistrationSerializer(data=attrs)
        self.service_account_serializer.is_valid(raise_exception=True)
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        sa = self.service_account_serializer.save()
        instance = super().create(validated_data)
        instance.is_accepted = True
        instance.user = sa
        instance.remote_addr = get_request_ip(request)
        instance.save()
        return instance
