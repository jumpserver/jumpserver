from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from common.db.models import JMSModel
from common.fields.model import PortField


class Endpoint(JMSModel):
    name = models.CharField(max_length=256, verbose_name=_('Name'), unique=True)
    host = models.CharField(max_length=256, verbose_name=_('Host'))
    # disabled value=0
    https_port = PortField(default=8443, verbose_name=_('HTTPS Port'))
    http_port = PortField(default=80, verbose_name=_('HTTP Port'))
    ssh_port = PortField(default=22, verbose_name=_('SSH Port'))
    rdp_port = PortField(default=3389, verbose_name=_('RDP Port'))
    mysql_port = PortField(default=3306, verbose_name=_('MySQL Port'))
    mariadb_port = PortField(default=3306, verbose_name=_('MariaDB Port'))
    postgresql_port = PortField(default=5432, verbose_name=_('PostgreSQL Port'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        verbose_name = _('Endpoint')
        ordering = ('name',)

    def __str__(self):
        return self.name


class EndpointRule(JMSModel):
    name = models.CharField(max_length=256, verbose_name=_('Name'), unique=True)
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
