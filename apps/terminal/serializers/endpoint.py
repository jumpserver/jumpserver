from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from common.drf.serializers import BulkModelSerializer
from acls.serializers.rules import ip_group_help_text, ip_group_child_validator
from ..models import Endpoint, EndpointRule

__all__ = ['EndpointSerializer', 'EndpointRuleSerializer', 'SmartEndpointSerializer']


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


class SmartEndpointSerializer(serializers.Serializer):
    match_protocol = serializers.CharField(
        max_length=1024, allow_null=False, allow_blank=False, label=_('Protocol')
    )
    match_target_ip = serializers.CharField(
        max_length=1024, allow_null=False, allow_blank=True, label=_('Target IP')
    )
    smart_host = serializers.SerializerMethodField(label=_('Host'))
    smart_port = serializers.SerializerMethodField(label=_('Port'))
    smart_url = serializers.SerializerMethodField(label=_('Url'))

    _endpoint = None

    class Meta:
        fields = [
            'match_protocol', 'match_target_ip',
            'smart_host', 'smart_port', 'smart_url',
        ]

    def match_endpoint(self, obj):
        if self._endpoint:
            return self._endpoint
        protocol = obj.get('match_protocol')
        target_ip = obj.get('match_target_ip')
        endpoint = EndpointRule.match_endpoint(target_ip, protocol)
        if not endpoint:
            endpoint = Endpoint(**{
                'name': 'Default endpoint (tmp)',
                'host': self.context['request'].get_host().split(':')[0]
            })
        self._endpoint = endpoint
        return self._endpoint

    def get_smart_host(self, obj):
        endpoint = self.match_endpoint(obj)
        return endpoint.host

    def get_smart_port(self, obj):
        protocol = obj.get('match_protocol')
        endpoint = self.match_endpoint(obj)
        return endpoint.get_port(protocol)

    def get_smart_url(self, obj):
        host = self.get_smart_host(obj)
        port = self.get_smart_port(obj)
        return f'{host}:{port}'


class EndpointRuleSerializer(BulkModelSerializer):
    ip_group = serializers.ListField(
        default=['*'], label=_('IP'), help_text=ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator])
    )
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
