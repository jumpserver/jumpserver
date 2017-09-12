# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ['TaskConfig', 'InstallConfig']


class TaskConfig(models.Model):
    TASK_TYPE = (
        ('install', 'Install'),
        ('generic', 'Generic'),
    )
    """这是所有配置项的名称显示"""
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    desc = models.CharField(max_length=2000, null=True, blank=True, verbose_name=_('Description'))
    type = models.CharField(max_length=20, default='generic', choices=TASK_TYPE)
    allowed_delete = models.BooleanField(default=True, verbose_name=_('Allowed Delete'))

    def __unicode__(self):
        return self.name

    __str__ = __unicode__


class InstallConfig(models.Model):
    """安装任务的具体配置"""
    config = models.OneToOneField(to=TaskConfig, on_delete=models.CASCADE, related_name='install_config')
    hybris_path = models.CharField(max_length=50, verbose_name=_('Hybris Source Path'),
                                   help_text=_('Hybris Source Path Help'), default='/opt/binaries/hybris.zip')
    deploy_path = models.CharField(max_length=500, verbose_name=_('Deploy Path'), default='/opt/hybris')
    deploy_jrebel = models.BooleanField(default=False, verbose_name=_('Deploy Jrebel'),
                                        help_text=_('Deploy Jrebel Help'))
    jrebel_path = models.CharField(max_length=500, verbose_name=_('Jrebel Path'), default='/opt/jrebel')
    db_driver_url = models.CharField(max_length=2000, verbose_name=_('Db Driver Url'),
                                     help_text=_('Db Driver Url Help'))


class DeployConfig(models.Model):
    """代码部署任务的具体配置"""
    config = models.OneToOneField(to=TaskConfig, on_delete=models.CASCADE, related_name='deploy_config')
    git_repo = models.CharField(max_length=500, verbose_name=_('Git Repo'))
    git_private_key = models.CharField(max_length=5000, blank=True, verbose_name=_('Git Private Key'))
    git_username = models.CharField(max_length=100, blank=True, verbose_name=_('Git Username'))
    git_password = models.CharField(max_length=100, blank=True, verbose_name=_('Git Password'))
    hybris_path = models.CharField(max_length=500, verbose_name=_('Hybris Path'), default='/opt/hybris')
