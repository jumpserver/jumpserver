from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel
from assets.models import Host


__all__ = ['AppletHost', 'AppletHostDeployment']


class AppletHost(Host):
    LOCKING_ORG = '00000000-0000-0000-0000-000000000004'

    account_automation = models.BooleanField(default=False, verbose_name=_('Account automation'))
    deploy_options = models.JSONField(default=dict, verbose_name=_('Deploy options'))
    inited = models.BooleanField(default=False, verbose_name=_('Inited'))
    date_inited = models.DateTimeField(null=True, blank=True, verbose_name=_('Date inited'))
    date_synced = models.DateTimeField(null=True, blank=True, verbose_name=_('Date synced'))
    status = models.CharField(max_length=16, verbose_name=_('Status'))
    terminal = models.OneToOneField(
        'terminal.Terminal', on_delete=models.PROTECT, null=True, blank=True,
        related_name='applet_host', verbose_name=_('Terminal')
    )
    applets = models.ManyToManyField(
        'Applet', verbose_name=_('Applet'),
        through='AppletPublication',  through_fields=('host', 'applet'),
    )

    def __str__(self):
        return self.name


class AppletHostDeployment(JMSBaseModel):
    host = models.ForeignKey('AppletHost', on_delete=models.CASCADE, verbose_name=_('Hosting'))
    initial = models.BooleanField(default=False, verbose_name=_('Initial'))
    status = models.CharField(max_length=16, default='', verbose_name=_('Status'))
    date_start = models.DateTimeField(null=True, verbose_name=_('Date start'), db_index=True)
    date_finished = models.DateTimeField(null=True, verbose_name=_("Date finished"))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def start(self, **kwargs):
        from ...automations.deploy_applet_host import DeployAppletHostManager
        manager = DeployAppletHostManager(self)
        manager.run(**kwargs)
