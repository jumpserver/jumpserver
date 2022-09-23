from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from common.utils import lazyproperty
from .base import BaseAccount

__all__ = ['Account', 'AccountTemplate']


class Account(BaseAccount):
    asset = models.ForeignKey(
        'assets.Asset', related_name='accounts',
        on_delete=models.CASCADE, verbose_name=_('Asset')
    )
    su_from = models.ForeignKey(
        'assets.Account', related_name='su_to', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Su from")
    )
    version = models.IntegerField(default=0, verbose_name=_('Version'))
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Account')
        unique_together = [
            ('username', 'asset', 'secret_type'),
            ('name', 'asset'),
        ]
        permissions = [
            ('view_accountsecret', _('Can view asset account secret')),
            ('change_accountsecret', _('Can change asset account secret')),
            ('view_historyaccount', _('Can view asset history account')),
            ('view_historyaccountsecret', _('Can view asset history account secret')),
        ]

    @lazyproperty
    def platform(self):
        return self.asset.platform

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset.name)


class AccountTemplate(BaseAccount):
    class Meta:
        verbose_name = _('Account template')
        unique_together = (
            ('name', 'org_id'),
        )

    def __str__(self):
        return self.username
