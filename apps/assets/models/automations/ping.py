from django.utils.translation import gettext_lazy as _

from assets.const import AutomationTypes
from .base import AssetBaseAutomation

__all__ = ['PingAutomation']


class PingAutomation(AssetBaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.ping
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Ping asset")
