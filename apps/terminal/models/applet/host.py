from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.models import Host
from ops.ansible import PlaybookRunner, JMSInventory


__all__ = ['AppletHost']


class AppletHost(Host):
    account_automation = models.BooleanField(default=False, verbose_name=_('Account automation'))
    initialized = models.BooleanField(default=False, verbose_name=_('Initialized'))
    date_inited = models.DateTimeField(null=True, blank=True, verbose_name=_('Date initialized'))
    date_synced = models.DateTimeField(null=True, blank=True, verbose_name=_('Date synced'))
    status = models.CharField(max_length=16, verbose_name=_('Status'))
    applets = models.ManyToManyField(
        'Applet', verbose_name=_('Applet'),
        through='AppletPublication',  through_fields=('host', 'applet'),
    )

    def deploy(self):
        inventory = JMSInventory([self])
        playbook = PlaybookRunner(inventory, 'applets.yml')
        playbook.run()

    def __str__(self):
        return self.name

