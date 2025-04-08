from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from common.serializers import BulkModelSerializer
from common.serializers.fields import ObjectRelatedField
from ..models import Endpoint, EndpointRule

__all__ = ['EndpointSerializer', 'EndpointRuleSerializer']


class EndpointSerializer(BulkModelSerializer):
    class Meta:
        model = Endpoint
        fields_mini = ['id', 'name']
        fields_small = [
            'host', 'https_port', 'http_port', 'ssh_port', 'rdp_port',
            'mysql_port', 'mariadb_port', 'postgresql_port', 'redis_port', 'vnc_port',
            'oracle_port', 'sqlserver_port', 'is_active'
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
    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        model_fields = self.Meta.model._meta.fields
        for field in model_fields:
            if field.name.endswith('_port'):
                kwargs = extra_kwargs.get(field.name, {})
                kwargs = {'default': field.default, **kwargs}
                extra_kwargs[field.name] = kwargs
        return extra_kwargs

    def validate_is_active(self, value):
        if self.instance and str(self.instance.id) == Endpoint.default_id:
            # 默认端点不能禁用
            return True
        else:
            return value


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
