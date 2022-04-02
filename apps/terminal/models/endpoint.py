from django.db import models
from urllib.parse import urlparse
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from common.db.models import JMSModel
from django.conf import settings


class ProtocolChoices(models.TextChoices):
    http = 'http', 'HTTP'
    https = 'https', 'HTTPS'
    ssh = 'ssh', 'SSH'
    rdp = 'rdp', 'RDP'
    mysql = 'mysql', 'MySQL'
    mariadb = 'mariadb', 'MariaDB'
    postgresql = 'postgresql', 'PostgreSQL'
    # oracle = 'oracle', 'Oracle'
    # sqlserver = 'sqlserver', 'SQLServer'
    # redis = 'redis', 'Redis'
    # mongodb = 'mongodb', 'MongoDB'

    @property
    def default_port(self):
        default_port_mapper: dict = {
            self.http: 80,
            self.https: 8443,
            self.ssh: 22,
            self.rdp: 3389,
            self.mysql: 3306,
            self.mariadb: 3306,
            self.postgresql: 5432,
            # self.oracle: 1521,
            # self.sqlserver: 1433,
            # self.redis: 6379,
            # self.mongodb: 27017
        }
        assert self.name in default_port_mapper, 'No support protocol: {}'.format(self.name)
        return default_port_mapper[self.name]


class EndpointProtocol(models.Model):
    name = models.CharField(
        max_length=64, choices=ProtocolChoices.choices, null=False, blank=False,
        verbose_name=_('Name')
    )
    port = models.IntegerField(
        null=False, blank=False, verbose_name=_('Port'),
        validators=[MinValueValidator(1), MaxValueValidator(65535)]
    )
    enabled = models.BooleanField(default=True, verbose_name=_('Enabled'))
    builtin = models.BooleanField(default=False, verbose_name=_('Builtin'))

    class Meta:
        verbose_name = _('Endpoint protocol')
        unique_together = (('name', 'port', 'enabled'),)
        ordering = ('name',)

    def __str__(self):
        builtin = ' [built-in]' if self.builtin else ''
        enabled = ' [Enabled]' if self.enabled else ''
        return f'{self.name}/{self.port}{builtin}{enabled}'

    @classmethod
    def get_merged_protocols_with_default(cls, protocols, default_enabled=True):
        protocol_names = protocols.values_list('name', flat=True)
        default_protocols = cls.get_or_create_default_protocols(enabled=default_enabled)
        to_default_protocol_ids = [p.id for p in default_protocols if p.name not in protocol_names]
        protocol_ids = list(protocols.values_list('id', flat=True))
        protocol_ids.extend(to_default_protocol_ids)
        return cls.objects.filter(id__in=protocol_ids)

    @classmethod
    def get_or_create_default_protocols(cls, name=None, enabled=None):
        if name is None:
            protocols = ProtocolChoices
        else:
            assert name in ProtocolChoices.names, (
                _('No support protocol: {}, Options: {}').format(name, ProtocolChoices.names)
            )
            protocols = [getattr(ProtocolChoices, name)]
        data = []
        for p in protocols:
            d = {'name': p.name, 'port': p.default_port, 'builtin': True}
            if enabled is None or enabled is True:
                d.update({'enabled': True})
                data.append(d)
            elif enabled is None or enabled is False:
                d.update({'enabled': False})
                data.append(d)
            else:
                continue
        return cls.get_or_create_protocols(data)

    @classmethod
    def get_or_create_protocols(cls, data):
        # TODO: data is queryset
        protocol_ids = []
        for d in data:
            protocol = cls.get_or_create_protocol(d)
            protocol_ids.append(protocol.id)
        return cls.objects.filter(id__in=protocol_ids)

    @classmethod
    def get_or_create_protocol(cls, data):
        protocol, created = cls.objects.get_or_create(**data, defaults=data)
        return protocol


class Endpoint(JMSModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    host = models.CharField(max_length=256, null=True, blank=True, verbose_name=_('Host'))
    protocols = models.ManyToManyField(
        'terminal.EndpointProtocol', related_name='endpoint', verbose_name=_('ProtocolChoices')
    )
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        verbose_name = _('Endpoint')
        ordering = ('name',)

    def __str__(self):
        return self.name

    def reset_protocols_to_default(self, only_nonexistent=True, enabled=True):
        default_protocols = EndpointProtocol.get_or_create_default_protocols(enabled=enabled)
        if not only_nonexistent:
            self.protocols.set(default_protocols)

        current_protocols = self.protocols.all().values_list('name', flat=True)
        to_protocols = [p for p in default_protocols if p.name not in current_protocols]
        self.protocols.set(to_protocols)


class EndpointRule(JMSModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    ip_group = models.TextField(default='', blank=True, verbose_name=_('IP group'))
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
