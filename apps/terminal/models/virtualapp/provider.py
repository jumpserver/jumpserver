from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['AppProvider', ]


class AppProvider(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    hostname = models.CharField(max_length=128, verbose_name=_('Hostname'))
    terminal = models.OneToOneField(
        'terminal.Terminal', on_delete=models.CASCADE, null=True, blank=True,
        related_name='app_provider', verbose_name=_('Terminal')
    )
    apps = models.ManyToManyField(
        'VirtualApp', verbose_name=_('Virtual app'),
        through='VirtualAppPublication', through_fields=('provider', 'app'),
    )

    class Meta:
        ordering = ('-date_created',)

    @property
    def load(self):
        if not self.terminal:
            return 'offline'
        return self.terminal.load
