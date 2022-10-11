from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from common.drf.serializers import BulkModelSerializer
from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from ..utils import db_port_manager
from ..models import Endpoint, EndpointRule


__all__ = ['EndpointSerializer', 'EndpointRuleSerializer']


class EndpointSerializer(BulkModelSerializer):
    # 解决 luna 处理繁琐的问题, 返回 magnus 监听的当前 db 的 port
    magnus_listen_db_port = serializers.SerializerMethodField(label=_('Magnus listen db port'))
    magnus_listen_port_range = serializers.CharField(
        max_length=128, default=db_port_manager.magnus_listen_port_range, read_only=True,
        label=_('Magnus Listen port range'),
        help_text=_(
            'The range of ports that Magnus listens on is modified in the configuration file'
        )
    )

    class Meta:
        model = Endpoint
        fields_mini = ['id', 'name']
        fields_small = [
            'host',
            'https_port', 'http_port', 'ssh_port', 'rdp_port',
            'magnus_listen_db_port', 'magnus_listen_port_range',
        ]
        fields = fields_mini + fields_small + [
            'comment', 'date_created', 'date_updated', 'created_by'
        ]
        extra_kwargs = {
            'https_port': {'default': 443},
            'http_port': {'default': 80},
            'ssh_port': {'default': 2222},
            'rdp_port': {'default': 3389},
        }

    def get_magnus_listen_db_port(self, obj: Endpoint):
        view = self.context.get('view')
        if not view or view.action not in ['smart']:
            return 0
        return obj.get_port(view.target_instance, view.target_protocol)


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
