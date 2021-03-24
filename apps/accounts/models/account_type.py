from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin


__all__ = ['AccountType']


class AccountType(CommonModelMixin, models.Model):
    """ 账号类型: 用来标识此类型账号所需要的其他附加字段 """
    class CategoryChoices(models.TextChoices):
        os = 'operating_system', 'Operating System'
        cloud = 'cloud_service', 'Cloud Service'
        website = 'website', ' Website'
        db = 'database', 'Database'
        application = 'application', 'Application'
        network_device = 'network_device', 'Network Device'

    class SecretTypeChoices(models.TextChoices):
        ssh_key = 'ssh_key', 'SSH Key'
        password = 'password', 'Password'
        cert = 'cert', 'Cert'
        token = 'token', 'Token'
        text = 'text', 'Text'

    display_name = models.CharField(max_length=1024, verbose_name=_('Display name'))
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    parent = models.ForeignKey(
        'AccountType', on_delete=models.PROTECT, default=None, null=True, verbose_name=_('Base')
    )
    category = models.CharField(
        default=CategoryChoices.os, choices=CategoryChoices.choices, verbose_name=_('Category')
    )
    secret_type = models.CharField(
        default=SecretTypeChoices.password, choices=SecretTypeChoices.choices,
        verbose_name=_('Secret typ')
    )
    fields = models.ManyToManyField('Field', related_name='account_type', verbose_name=_('Fields'))
    comment = models.TextField(null=True, blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name
