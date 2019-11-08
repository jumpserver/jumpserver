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

    def create(self, validated_data):
        validated_data.pop('action')
        return super().create(validated_data)

    def update(self, instance, validated_data):
        action = validated_data.get("action")
        user = self.context["request"].user
        if action and user not in instance.assignees.all():
            error = {"action": "Only assignees can update"}
            raise serializers.ValidationError(error)
        instance = super().update(instance, validated_data)
        if action:
            instance.perform_action(action, user)
        return instance


class LoginConfirmTicketActionSerializer(serializers.ModelSerializer):
    comment = serializers.CharField(allow_blank=True)

    class Meta:
        model = LoginConfirmTicket
        fields = ['action']

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
