from django.db import models
from django.utils.translation import ugettext_lazy as _

from accounts.const import AutomationTypes
from .base import AccountBaseAutomation
from .change_secret import ChangeSecretMixin

__all__ = ['PushAccountAutomation']


class PushAccountAutomation(AccountBaseAutomation, ChangeSecretMixin):
    username = models.CharField(max_length=128, verbose_name=_('Username'))

    def set_period_schedule(self):
        pass

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.push_account
        self.is_periodic = False
        super().save(*args, **kwargs)

    def to_attr_json(self):
        attr_json = super().to_attr_json()
        attr_json.update({
            'username': self.username
        })
        return attr_json

    class Meta:
        verbose_name = _("Push asset account")
