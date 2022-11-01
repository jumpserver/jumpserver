from django.utils.translation import ugettext_lazy as _

from assets.const import AutomationTypes
from .base import BaseAutomation

__all__ = ['PingAutomation']


class PingAutomation(BaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.ping
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Ping asset")
