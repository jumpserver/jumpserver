from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['VirtualHost', ]


class VirtualHost(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    hostname = models.CharField(max_length=128, verbose_name=_('Hostname'))
    terminal = models.OneToOneField(
        'terminal.Terminal', on_delete=models.CASCADE, null=True, blank=True,
        related_name='virtual_host', verbose_name=_('Terminal')
    )
    apps = models.ManyToManyField(
        'VirtualApp', verbose_name=_('VirtualApp'),
        through='VirtualAppPublication', through_fields=('vhost', 'app'),
    )

    class Meta:
        ordering = ('-date_created',)

    @property
    def load(self):
        if not self.terminal:
            return 'offline'
        return self.terminal.load
