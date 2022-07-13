from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from .user import ProtocolMixin
from .base import BaseUser


__all__ = ['Account']


class Account(BaseUser, ProtocolMixin):
    protocol = models.CharField(max_length=16, choices=ProtocolMixin.Protocol.choices,
                                default='ssh', verbose_name=_('Protocol'))
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    version = models.IntegerField(default=1, verbose_name=_('Version'))
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Account')
        unique_together = [('username', 'asset')]
        permissions = [
            ('view_assetaccountsecret', _('Can view asset account secret')),
            ('change_assetaccountsecret', _('Can change asset account secret')),
            ('view_assethistoryaccount', _('Can view asset history account')),
            ('view_assethistoryaccountsecret', _('Can view asset history account secret')),
        ]

    def __str__(self):
        return '{}//{}@{}'.format(self.protocol, self.username, self.asset.hostname)
