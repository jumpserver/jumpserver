from django.utils.translation import ugettext_lazy as _

from ops.const import StrategyChoice
from .base import BaseAutomation


class VerifySecretAutomation(BaseAutomation):
    class Meta:
        verbose_name = _("Verify secret automation")

    def save(self, *args, **kwargs):
        self.type = 'verify_secret'
        super().save(*args, **kwargs)
