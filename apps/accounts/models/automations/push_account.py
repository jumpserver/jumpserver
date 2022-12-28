from django.db import models
from django.utils.translation import ugettext_lazy as _

from assets.const import AutomationTypes
from .base import BaseAutomation
from .change_secret import ChangeSecretMixin

__all__ = ['PushAccountAutomation']


class PushAccountAutomation(BaseAutomation, ChangeSecretMixin):
    accounts = None
    username = models.CharField(max_length=128, verbose_name=_('Username'))

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.push_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Push asset account")
