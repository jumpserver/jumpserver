from django.utils.translation import ugettext_lazy as _

from assets.const import AutomationTypes
from .base import BaseAutomation

__all__ = ['GatherAccountsAutomation']


class GatherAccountsAutomation(BaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.gather_accounts
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Gather asset accounts")
