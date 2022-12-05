from django.utils.translation import ugettext_lazy as _

from assets.const import AutomationTypes
from .base import BaseAutomation

__all__ = ['PushAccountAutomation']


class PushAccountAutomation(BaseAutomation):

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.push_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Push asset account")
