from django.utils.translation import ugettext_lazy as _

from .base import BaseAutomation


class VerifyAccountAutomation(BaseAutomation):
    class Meta:
        verbose_name = _("Verify account automation")

    def save(self, *args, **kwargs):
        self.type = 'verify_account'
        super().save(*args, **kwargs)
