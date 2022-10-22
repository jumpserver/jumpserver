from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel


__all__ = ['Applet', 'AppletPublication']


class Applet(JMSBaseModel):
    class Type(models.TextChoices):
        app = 'app', _('App')
        web = 'web', _('Web')
    name = models.CharField(max_length=128, verbose_name=_('Name'), unique=True)
    version = models.CharField(max_length=16, verbose_name=_('Version'))
    type = models.CharField(max_length=16, choices=Type.choices, verbose_name=_('Type'))
    icon = models.ImageField(upload_to='applet/icon', verbose_name=_('Icon'))
    author = models.CharField(max_length=128, verbose_name=_('Author'))
    protocols = models.JSONField(default=list, verbose_name=_('Protocol'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name


class AppletPublication(JMSBaseModel):
    applet = models.ForeignKey('Applet', on_delete=models.PROTECT, verbose_name=_('Applet'))
    provider = models.ForeignKey('AppletProvider', on_delete=models.PROTECT, verbose_name=_('Provider'))
    status = models.CharField(max_length=16, verbose_name=_('Status'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        unique_together = ('applet', 'provider')
