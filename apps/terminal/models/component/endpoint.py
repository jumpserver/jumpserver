from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.models import Asset
from common.db.fields import PortField
from common.db.models import JMSBaseModel
from common.utils.ip import contains_ip


class Endpoint(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    host = models.CharField(max_length=256, blank=True, verbose_name=_('Host'))
    # value=0 表示 disabled
    https_port = PortField(default=443, verbose_name=_('HTTPS port'))
    http_port = PortField(default=80, verbose_name=_('HTTP port'))
    ssh_port = PortField(default=2222, verbose_name=_('SSH port'))
    rdp_port = PortField(default=3389, verbose_name=_('RDP port'))
    mysql_port = PortField(default=33061, verbose_name=_('MySQL port'))
    mariadb_port = PortField(default=33062, verbose_name=_('MariaDB port'))
    postgresql_port = PortField(default=54320, verbose_name=_('PostgreSQL port'))
    redis_port = PortField(default=63790, verbose_name=_('Redis port'))
    sqlserver_port = PortField(default=14330, verbose_name=_('SQLServer port'))

    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    default_id = '00000000-0000-0000-0000-000000000001'

    class Meta:
        verbose_name = _('Endpoint')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_port(self, target_instance, protocol):
        from terminal.utils import db_port_manager
        from assets.const import DatabaseTypes, Protocol

        if isinstance(target_instance, Asset) and \
                target_instance.is_type(DatabaseTypes.ORACLE) and \
                protocol == Protocol.oracle:
            port = db_port_manager.get_port_by_db(target_instance)
        else:
            if protocol in [Protocol.sftp, Protocol.telnet]:
                protocol = Protocol.ssh
            port = getattr(self, f'{protocol}_port', 0)
        return port

    def is_default(self):
        return str(self.id) == self.default_id

    def delete(self, using=None, keep_parents=False):
        if self.is_default():
            return
        return super().delete(using, keep_parents)

    def is_valid_for(self, target_instance, protocol):
        if self.is_default():
            return True
        if self.get_port(target_instance, protocol) != 0:
            return True
        return False

    @classmethod
    def get_or_create_default(cls, request=None):
        data = {
            'id': cls.default_id,
            'name': 'Default',
            'host': '',
            'https_port': 0,
            'http_port': 0,
        }
        endpoint, created = cls.objects.get_or_create(id=cls.default_id, defaults=data)
        return endpoint

    @classmethod
    def handle_endpoint_host(cls, endpoint, request=None):
        if not endpoint.host and request:
            # 动态添加 current request host
            host_port = request.get_host()
            # IPv6
            if host_port.startswith('['):
                host = host_port.split(']:')[0].rstrip(']') + ']'
            else:
                host = host_port.split(':')[0]
            endpoint.host = host
        return endpoint

    @classmethod
    def match_by_instance_label(cls, instance, protocol, request=None):
        from assets.models import Asset
        from terminal.models import Session
        if isinstance(instance, Session):
            instance = instance.get_asset()
        if not isinstance(instance, Asset):
            return None
        values = instance.labels.filter(label__name='endpoint').values_list('label__value', flat=True)
        if not values:
            return None
        endpoints = cls.objects.filter(name__in=list(values)).order_by('-date_updated')
        for endpoint in endpoints:
            if endpoint.is_valid_for(instance, protocol):
                endpoint = cls.handle_endpoint_host(endpoint, request)
                return endpoint


class EndpointRule(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    ip_group = models.JSONField(default=list, verbose_name=_('IP group'))
    priority = models.IntegerField(
        verbose_name=_("Priority"), validators=[MinValueValidator(1), MaxValueValidator(100)],
        unique=True, help_text=_("1-100, the lower the value will be match first"),
    )
    endpoint = models.ForeignKey(
        'terminal.Endpoint', null=True, blank=True, related_name='rules',
        on_delete=models.SET_NULL, verbose_name=_("Endpoint"),
    )
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    class Meta:
        verbose_name = _('Endpoint rule')
        ordering = ('priority', 'is_active', 'name')

    def __str__(self):
        return f'{self.name}({self.priority})'

    @classmethod
    def match(cls, target_instance, target_ip, protocol):
        for endpoint_rule in cls.objects.prefetch_related('endpoint').filter(is_active=True):
            if not contains_ip(target_ip, endpoint_rule.ip_group):
                continue
            if not endpoint_rule.endpoint:
                continue
            if not endpoint_rule.endpoint.is_valid_for(target_instance, protocol):
                continue
            return endpoint_rule

    @classmethod
    def match_endpoint(cls, target_instance, target_ip, protocol, request=None):
        endpoint_rule = cls.match(target_instance, target_ip, protocol)
        if endpoint_rule:
            endpoint = endpoint_rule.endpoint
        else:
            endpoint = Endpoint.get_or_create_default(request)
        endpoint = Endpoint.handle_endpoint_host(endpoint, request)
        return endpoint
