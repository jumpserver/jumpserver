from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from common.drf.serializers import BulkModelSerializer
from ..models import Endpoint, EndpointRule

__all__ = ['EndpointSerializer', 'EndpointRuleSerializer']


class EndpointSerializer(BulkModelSerializer):

    class Meta:
        model = Endpoint
        fields_mini = ['id', 'name']
        fields_small = [
            'host',
            'https_port', 'http_port', 'ssh_port',
            'rdp_port', 'mysql_port', 'mariadb_port',
            'postgresql_port',
        ]
        fields = fields_mini + fields_small + [
            'comment', 'date_created', 'date_updated', 'created_by'
        ]
        extra_kwargs = {
            'https_port': {'default': 8443},
            'http_port': {'default': 80},
            'ssh_port': {'default': 22},
            'rdp_port': {'default': 3389},
            'mysql_port': {'default': 3306},
            'mariadb_port': {'default': 3306},
            'postgresql_port': {'default': 5432},
        }


class EndpointRuleSerializer(BulkModelSerializer):
    endpoint_display = serializers.ReadOnlyField(source='endpoint.name', label=_('Endpoint'))

    class Meta:
        model = EndpointRule
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['ip_group', 'priority']
        fields_fk = ['endpoint', 'endpoint_display']
        fields = fields_mini + fields_small + fields_fk + [
            'comment', 'date_created', 'date_updated', 'created_by'
        ]
        extra_kwargs = {
        }
