# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from common.utils import get_request_ip
from users.serializers_v2 import ServiceAccountSerializer
from ..models import Terminal


__all__ = ['TerminalSerializer', 'TerminalRegistrationSerializer']


class TerminalSerializer(serializers.ModelSerializer):
    sa_serializer_class = ServiceAccountSerializer
    sa_serializer = None

    class Meta:
        model = Terminal
        fields = [
            'id', 'name', 'remote_addr', 'command_storage',
            'replay_storage', 'user', 'is_accepted', 'is_deleted',
            'date_created', 'comment'
        ]
        read_only_fields = ['remote_addr', 'user', 'date_created']

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=raise_exception)
        if not valid:
            return valid
        data = {'name': self.validated_data.get('name')}
        kwargs = {'data': data}
        if self.instance and self.instance.user:
            kwargs['instance'] = self.instance.user
        self.sa_serializer = ServiceAccountSerializer(**kwargs)
        valid = self.sa_serializer.is_valid(raise_exception=True)
        return valid

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        sa = self.sa_serializer.save()
        instance.user = sa
        instance.save()
        return instance

    def create(self, validated_data):
        request = self.context.get('request')
        instance = super().create(validated_data)
        instance.is_accepted = True
        if request:
            instance.remote_addr = get_request_ip(request)
        instance.save()
        return instance


class TerminalRegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    comment = serializers.CharField(max_length=128)
    service_account = ServiceAccountSerializer(read_only=True)
