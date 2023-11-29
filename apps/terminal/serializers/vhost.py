from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from terminal import const
from ..models import VirtualHost

__all__ = ['VirtualHostSerializer', 'VirtualHostContainerSerializer',]


class VirtualHostSerializer(serializers.ModelSerializer):
    load = LabeledChoiceField(
        read_only=True, label=_('Load status'), choices=const.ComponentLoad.choices,
    )

    class Meta:
        model = VirtualHost
        field_mini = ['id', 'name', 'hostname']
        read_only_fields = [
            'date_created', 'date_updated',
        ]
        fields = field_mini + ['load', 'terminal'] + read_only_fields


class VirtualHostContainerSerializer(serializers.Serializer):
    container_id = serializers.CharField(label=_('Container ID'))
    container_image = serializers.CharField(label=_('Container Image'))
    container_name = serializers.CharField(label=_('Container Name'))
    container_status = serializers.CharField(label=_('Container Status'))
    container_ports = serializers.ListField(child=serializers.CharField(), label=_('Container Ports'))

