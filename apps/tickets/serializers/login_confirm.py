# -*- coding: utf-8 -*-
#
from rest_framework import serializers

from .base import TicketSerializer
from ..models import LoginConfirmTicket


__all__ = ['LoginConfirmTicketSerializer', 'LoginConfirmTicketActionSerializer']


class LoginConfirmTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginConfirmTicket
        fields = TicketSerializer.Meta.fields + [
            'ip', 'city', 'action'
        ]
        read_only_fields = TicketSerializer.Meta.read_only_fields


class LoginConfirmTicketActionSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(allow_blank=True)

    class Meta:
        model = LoginConfirmTicket
        fields = ['action', 'comment']

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
