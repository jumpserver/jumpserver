from django.utils.translation import ugettext_lazy as _

from assets.const import AutomationTypes
from .base import BaseAutomation

__all__ = ['VerifyAccountAutomation']


class VerifyAccountAutomation(BaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.verify_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Verify asset account")
