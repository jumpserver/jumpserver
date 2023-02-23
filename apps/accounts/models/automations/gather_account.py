from django.db import models
from django.utils.translation import ugettext_lazy as _

from accounts.const import AutomationTypes
from orgs.mixins.models import JMSOrgBaseModel
from .base import AccountBaseAutomation

__all__ = ['GatherAccountsAutomation', 'GatheredAccount']


class GatheredAccount(JMSOrgBaseModel):
    present = models.BooleanField(default=True, verbose_name=_("Present"))
    date_last_login = models.DateTimeField(null=True, verbose_name=_("Date last login"))
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_("Asset"))
    username = models.CharField(max_length=32, blank=True, db_index=True, verbose_name=_('Username'))
    address_last_login = models.CharField(max_length=39, default='', verbose_name=_("Address last login"))

    @property
    def address(self):
        return self.asset.address

    class Meta:
        verbose_name = _('Gather account automation')
        unique_together = [
            ('username', 'asset'),
        ]
        ordering = ['asset']

    def __str__(self):
        return '{}: {}'.format(self.asset, self.username)


class GatherAccountsAutomation(AccountBaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.gather_accounts
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Gather asset accounts")
