from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from common.db.models import JMSModel
from common.fields.model import PortField
from common.utils.ip import contains_ip


class Endpoint(JMSModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    host = models.CharField(max_length=256, blank=True, verbose_name=_('Host'))
    # disabled value=0
    https_port = PortField(default=443, verbose_name=_('HTTPS Port'))
    http_port = PortField(default=80, verbose_name=_('HTTP Port'))
    ssh_port = PortField(default=2222, verbose_name=_('SSH Port'))
    rdp_port = PortField(default=3389, verbose_name=_('RDP Port'))
    mysql_port = PortField(default=33060, verbose_name=_('MySQL Port'))
    mariadb_port = PortField(default=33061, verbose_name=_('MariaDB Port'))
    postgresql_port = PortField(default=54320, verbose_name=_('PostgreSQL Port'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    default_id = '00000000-0000-0000-0000-000000000001'

    class Meta:
        verbose_name = _('Endpoint')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def get_port(self, protocol):
        return getattr(self, f'{protocol}_port', 0)

    def is_default(self):
        return self.id == self.default_id

    def delete(self, using=None, keep_parents=False):
        if self.is_default():
            return
        return super().delete(using, keep_parents)

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
        if not endpoint.host and request:
            endpoint.host = request.get_host().split(':')[0]
        return endpoint


class EndpointRule(JMSModel):
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

    class Meta:
        verbose_name = _('Endpoint rule')
        ordering = ('priority', 'name')

    def __str__(self):
        return f'{self.name}({self.priority})'

    @classmethod
    def match(cls, target_ip, protocol):
        for endpoint_rule in cls.objects.all().prefetch_related('endpoint'):
            if not contains_ip(target_ip, endpoint_rule.ip_group):
                continue
            if not endpoint_rule.endpoint:
                continue
            if endpoint_rule.endpoint.is_default():
                return endpoint_rule
            if not endpoint_rule.endpoint.host:
                continue
            if endpoint_rule.endpoint.get_port(protocol) == 0:
                continue
            return endpoint_rule

    @classmethod
    def match_endpoint(cls, target_ip, protocol, request=None):
        endpoint_rule = cls.match(target_ip, protocol)
        if endpoint_rule:
            endpoint = endpoint_rule.endpoint
        else:
            endpoint = Endpoint.get_or_create_default(request)
        return endpoint
