from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['VirtualApp', 'VirtualAppPublication']


class VirtualApp(JMSBaseModel):
    name = models.SlugField(max_length=128, verbose_name=_('Name'), unique=True)
    image_name = models.CharField(max_length=128, verbose_name=_('Image name'))
    image_protocol = models.CharField(max_length=16, default='vnc', verbose_name=_('Image protocol'))
    image_port = models.IntegerField(default=5900, verbose_name=_('Image port'))
    protocols = models.JSONField(default=list, verbose_name=_('Protocol'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        verbose_name = _('Virtual app')

    def __str__(self):
        return self.name


class VirtualAppPublication(JMSBaseModel):
    vhost = models.ForeignKey(
        'VirtualHost', on_delete=models.CASCADE, related_name='publications', verbose_name=_('Virtual Host')
    )
    app = models.ForeignKey(
        'VirtualApp', on_delete=models.CASCADE, related_name='publications', verbose_name=_('Virtual App')
    )
    status = models.CharField(max_length=16, default='pending', verbose_name=_('Status'))

    class Meta:
        verbose_name = _('Virtual app publication')
        unique_together = ('vhost', 'app')
