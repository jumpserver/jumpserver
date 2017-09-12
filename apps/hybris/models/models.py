# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ['Template', 'InstallTemplate']


class Template(models.Model):
    TASK_TYPE = (
        ('install', 'Install'),
        ('generic', 'Generic'),
    )
    """这是所有模板的父类"""
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    desc = models.CharField(max_length=2000, null=True, blank=True, verbose_name=_('Description'))
    type = models.CharField(max_length=20, default='generic', choices=TASK_TYPE)
    allowed_delete = models.BooleanField(default=True, verbose_name=_('Allowed Delete'))

    def __unicode__(self):
        return self.name

    __str__ = __unicode__


class InstallTemplate(models.Model):
    """安装任务的模板"""
    config = models.OneToOneField(to=Template, on_delete=models.CASCADE, related_name='install_template')
    hybris_path = models.CharField(max_length=50, verbose_name=_('Hybris Source Path'),
                                   help_text=_('Hybris Source Path Help'), default='/opt/binaries/hybris.zip')
    deploy_path = models.CharField(max_length=500, verbose_name=_('Deploy Path'), default='/opt/hybris')
    deploy_jrebel = models.BooleanField(default=False, verbose_name=_('Deploy Jrebel'),
                                        help_text=_('Deploy Jrebel Help'))
    jrebel_path = models.CharField(max_length=500, verbose_name=_('Jrebel Path'), default='/opt/jrebel')
    db_driver_url = models.CharField(max_length=2000, verbose_name=_('Db Driver Url'),
                                     help_text=_('Db Driver Url Help'))


