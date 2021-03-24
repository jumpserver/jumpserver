from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin


__all__ = ['AccountType']


class AccountType(CommonModelMixin, models.Model):
    class SecretTypeChoices(models.TextChoices):
        ssh_key = 'ssh_key', 'SSH Key'
        password = 'password', 'Password'
        cert = 'cert', 'Cert'
        token = 'token', 'Token'
        text = 'text', 'Text'

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    base = models.ForeignKey(
        'AccountType', on_delete=models.PROTECT, default=None, null=True, verbose_name=_('Base')
    )
    secret_type = models.CharField(
        default=SecretTypeChoices.password, choices=SecretTypeChoices.choices,
        verbose_name=_('Secret typ')
    )
    fields = models.ManyToManyField('Field', related_name='account_type', verbose_name=_('Fields'))
    comment = models.TextField(null=True, blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name
