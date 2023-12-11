from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from common.serializers import BulkModelSerializer
from common.serializers.fields import ObjectRelatedField
from ..models import Endpoint, EndpointRule
from ..utils import db_port_manager

__all__ = ['EndpointSerializer', 'EndpointRuleSerializer']


class EndpointSerializer(BulkModelSerializer):
    # 解决 luna 处理繁琐的问题, 返回 magnus 监听的当前 db 的 port
    oracle_port = serializers.SerializerMethodField(label=_('Oracle port'))
    oracle_port_range = serializers.CharField(
        max_length=128, default=db_port_manager.oracle_port_range, read_only=True,
        label=_('Oracle port range'),
        help_text=_(
            'Oracle proxy server listen port is dynamic, Each additional Oracle '
            'database instance adds a port listener'
        )
    )

    class Meta:
        model = Endpoint
        fields_mini = ['id', 'name']
        fields_small = [
            'host', 'https_port', 'http_port', 'ssh_port', 'rdp_port',
            'mysql_port', 'mariadb_port', 'postgresql_port', 'redis_port',
            'oracle_port_range', 'oracle_port', 'sqlserver_port',
        ]
        fields = fields_mini + fields_small + [
            'comment', 'date_created', 'date_updated', 'created_by'
        ]
        extra_kwargs = {
            'host': {'help_text': _(
                'The host address accessed when connecting to assets, if it is empty, '
                'the access address of the current browser will be used '
                '(the default endpoint does not allow modification of the host)'
            )
            },
        }

    def get_oracle_port(self, obj: Endpoint):
        view = self.context.get('view')
        if not view or view.action not in ['smart']:
            return 0
        return obj.get_port(view.target_instance, view.target_protocol)

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        model_fields = self.Meta.model._meta.fields
        for field in model_fields:
            if field.name.endswith('_port'):
                kwargs = extra_kwargs.get(field.name, {})
                kwargs = {'default': field.default, **kwargs}
                extra_kwargs[field.name] = kwargs
        return extra_kwargs


class EndpointRuleSerializer(BulkModelSerializer):
    _ip_group_help_text = '{}, {} <br>{}'.format(
        _('The assets within this IP range, the following endpoint will be used for the connection'),
        _('If asset IP addresses under different endpoints conflict, use asset labels'),
        ip_group_help_text,
    )
    ip_group = serializers.ListField(
        default=['*'], label=_('Asset IP'), help_text=_ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator])
    )
    endpoint = ObjectRelatedField(
        allow_null=True, required=False, queryset=Endpoint.objects, label=_('Endpoint')
    )

    class Meta:
        model = EndpointRule
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['ip_group', 'priority']
        fields_fk = ['endpoint']
        fields = fields_mini + fields_small + fields_fk + [
            'comment', 'date_created', 'date_updated', 'created_by', 'is_active'
        ]
        extra_kwargs = {
            'priority': {'default': 50}
        }
