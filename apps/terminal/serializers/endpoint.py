from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from common.drf.serializers import BulkModelSerializer
from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from ..models import Endpoint, EndpointRule

__all__ = ['EndpointSerializer', 'EndpointRuleSerializer']


class EndpointSerializer(BulkModelSerializer):
    # 解决 luna 处理繁琐的问题，oracle_port 返回匹配到的端口
    oracle_port = serializers.SerializerMethodField(label=_('Oracle port'))

    class Meta:
        model = Endpoint
        fields_mini = ['id', 'name']
        fields_small = [
            'host',
            'https_port', 'http_port', 'ssh_port',
            'rdp_port', 'mysql_port', 'mariadb_port',
            'postgresql_port', 'redis_port',
            'oracle_11g_port', 'oracle_12c_port',
            'oracle_port',
        ]
        fields = fields_mini + fields_small + [
            'comment', 'date_created', 'date_updated', 'created_by'
        ]
        extra_kwargs = {
            'https_port': {'default': 443},
            'http_port': {'default': 80},
            'ssh_port': {'default': 2222},
            'rdp_port': {'default': 3389},
            'mysql_port': {'default': 33060},
            'mariadb_port': {'default': 33061},
            'postgresql_port': {'default': 54320},
            'redis_port': {'default': 63790},
            'oracle_11g_port': {'default': 15211},
            'oracle_12c_port': {'default': 15212},
        }

    def get_oracle_port(self, obj: Endpoint):
        view = self.context.get('view')
        if not view or view.action not in ['smart']:
            return 0
        return obj.get_port(view.target_protocol)


class EndpointRuleSerializer(BulkModelSerializer):
    _ip_group_help_text = '{} <br> {}'.format(
        ip_group_help_text,
        _('If asset IP addresses under different endpoints conflict, use asset labels')
    )
    ip_group = serializers.ListField(
        default=['*'], label=_('IP'), help_text=_ip_group_help_text,
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
