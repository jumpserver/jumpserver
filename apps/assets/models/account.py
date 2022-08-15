from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from common.db.models import JMSBaseModel
from common.db import fields
from .base import BaseUser, AbsConnectivity

__all__ = ['Account']


class Account(BaseUser, AbsConnectivity):
    token = fields.EncryptTextField(blank=True, null=True, verbose_name=_('Token'))
    privileged = models.BooleanField(verbose_name=_("Privileged account"), default=False)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    version = models.IntegerField(default=0, verbose_name=_('Version'))
    history = HistoricalRecords()

    class Meta:
        verbose_name = _('Account')
        unique_together = [('username', 'asset')]
        permissions = [
            ('view_accountsecret', _('Can view asset account secret')),
            ('change_accountsecret', _('Can change asset account secret')),
            ('view_historyaccount', _('Can view asset history account')),
            ('view_historyaccountsecret', _('Can view asset history account secret')),
        ]

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset.name)


class AccountTemplate(BaseUser, AbsConnectivity):
    type = models.CharField(
        max_length=16, choices=Account.Type.choices, default=Account.Type.common, verbose_name=_("Type")
    )

    class Meta:
        verbose_name = _('Account Template')

    def __str__(self):
        return '{}'.format(self.username)
