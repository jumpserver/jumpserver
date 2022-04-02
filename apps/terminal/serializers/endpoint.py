from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from common.drf.serializers import BulkModelSerializer
from ..models import Endpoint, EndpointRule, EndpointProtocol

__all__ = ['EndpointSerializer', 'EndpointRuleSerializer']


class ProtocolSerializer(serializers.ModelSerializer):
    name_display = serializers.ReadOnlyField(source='get_name_display', label=_('Name'))

    class Meta:
        model = EndpointProtocol
        fields = ['name', 'name_display', 'port', 'enabled']


class EndpointSerializer(BulkModelSerializer):
    protocols_group = serializers.ManyRelatedField(
        source='protocols', child_relation=ProtocolSerializer(), label=_('Protocol'),
        default=EndpointProtocol.get_or_create_default_protocols(enabled=True)
    )

    class Meta:
        model = Endpoint
        fields_mini = ['id', 'name']
        fields_m2m = ['protocols_group']
        fields = fields_mini + fields_m2m + [
            'date_created', 'date_updated', 'created_by'
        ]

    @staticmethod
    def validate_protocols_group(protocols):
        protocols = EndpointProtocol.get_or_create_protocols(protocols)
        protocols = EndpointProtocol.get_merged_protocols_with_default(protocols)
        return protocols


class EndpointRuleSerializer(BulkModelSerializer):
    class Meta:
        model = EndpointRule
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['ip_group', 'priority']
        fields_fk = ['endpoint']
        fields = fields_mini + fields_small + fields_fk + [
            'date_created', 'date_updated', 'created_by'
        ]
