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
            'http_port', 'https_port', 'ssh_port',
            'rdp_port', 'mysql_port', 'mariadb_port',
            'postgresql_port',
        ]
        fields = fields_mini + fields_small + [
            'comment', 'date_created', 'date_updated', 'created_by'
        ]


class EndpointRuleSerializer(BulkModelSerializer):
    class Meta:
        model = EndpointRule
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['ip_group', 'priority']
        fields_fk = ['endpoint']
        fields = fields_mini + fields_small + fields_fk + [
            'comment', 'date_created', 'date_updated', 'created_by'
        ]
