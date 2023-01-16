from django.utils.translation import ugettext_lazy as _

from accounts.const import AutomationTypes
from .base import AccountBaseAutomation

__all__ = ['GatherAccountsAutomation']


class GatherAccountsAutomation(AccountBaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.gather_accounts
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Gather asset accounts")
