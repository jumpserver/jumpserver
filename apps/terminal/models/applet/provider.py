from django.db import models
from django.utils.translation import gettext_lazy as _

from celery import current_app

from common.db.models import JMSBaseModel


__all__ = ['AppletProvider', 'ProviderDeployment']


class AppletProvider(JMSBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    asset = models.ForeignKey('assets.Asset', on_delete=models.PROTECT, verbose_name=_('Asset'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    account_automation = models.BooleanField(default=False, verbose_name=_('Account automation'))
    date_synced = models.DateTimeField(null=True, blank=True, verbose_name=_('Date synced'))
    status = models.CharField(max_length=16, verbose_name=_('Status'))
    applets = models.ManyToManyField(
        'Applet', verbose_name=_('Applet'),
        through='AppletPublication',  through_fields=('provider', 'applet'),
    )


class ProviderDeployment(JMSBaseModel):
    provider = models.ForeignKey('AppletProvider', on_delete=models.CASCADE, verbose_name=_('Provider'))
    status = models.CharField(max_length=16, verbose_name=_('Status'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def install(self):
        pass
