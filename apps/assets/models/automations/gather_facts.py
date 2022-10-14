from django.utils.translation import ugettext_lazy as _

from .base import BaseAutomation


__all__ = ['GatherFactsAutomation']


class GatherFactsAutomation(BaseAutomation):
    class Meta:
        verbose_name = _("Gather asset facts")

    def save(self, *args, **kwargs):
        self.type = 'gather_facts'
        super().save(*args, **kwargs)

