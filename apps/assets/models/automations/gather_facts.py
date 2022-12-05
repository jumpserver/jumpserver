from django.utils.translation import ugettext_lazy as _

from assets.const import AutomationTypes
from .base import BaseAutomation

__all__ = ['GatherFactsAutomation']


class GatherFactsAutomation(BaseAutomation):
    def save(self, *args, **kwargs):
        self.type = AutomationTypes.gather_facts
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Gather asset facts")
