from django.utils.module_loading import import_string
from rest_framework import serializers

from tickets.models import Ticket
from tickets.plugins import get_ticket_plugin
from tickets.workflow.definition import json_snapshot
from .ticket.ticket import TicketApplySerializer, TicketSerializer


class PluginTicketApplySerializer(TicketApplySerializer):
    """One submission envelope, with validation owned by the selected plugin."""
    type = serializers.ChoiceField(choices=[])
    request_data = serializers.JSONField(required=True)

    class Meta(TicketApplySerializer.Meta):
        fields = TicketApplySerializer.Meta.fields

    def validate(self, attrs):
        plugin = get_ticket_plugin(attrs['type'])
        if not plugin.self_service:
            raise serializers.ValidationError({'type': 'This ticket type is created by its business entrypoint.'})
        payload = json_snapshot(attrs.pop('request_data'))
        if not isinstance(payload, dict):
            raise serializers.ValidationError({'request_data': 'Request parameters must be an object.'})
        self.plugin = plugin
        if plugin.apply_serializer:
            serializer = import_string(plugin.apply_serializer)(context=self.context)
            allowed = {name for name, field in serializer.fields.items() if name.startswith('apply_') and not field.read_only}
            if payload.keys() - allowed:
                raise serializers.ValidationError({'request_data': 'Unknown request parameters.'})
            self.delegate = type(serializer)(data={**payload, **attrs}, context=self.context)
            self.delegate.is_valid(raise_exception=True)
            return dict(self.delegate.validated_data)
        attrs = super().validate(attrs)
        with_context = {**self.context, 'org_id': attrs['org_id']}
        serializer = plugin.get_request_serializer(data=payload, context=with_context)
        if not serializer.is_valid():
            raise serializers.ValidationError({'request_data': serializer.errors})
        attrs['request_data'] = json_snapshot(dict(serializer.data))
        return attrs

    def create(self, validated_data):
        if getattr(self, 'delegate', None) is not None:
            return self.delegate.create(validated_data)
        return Ticket.objects.create(**validated_data)

    def to_representation(self, instance):
        return TicketSerializer(instance, context=self.context).data
