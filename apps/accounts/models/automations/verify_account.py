from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from .base import AccountBaseAutomation

__all__ = ['VerifyAccountAutomation']


class VerifyAccountAutomation(AccountBaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.verify_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Verify asset account")
