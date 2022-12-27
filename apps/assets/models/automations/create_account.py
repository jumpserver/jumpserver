from django.db import models
from django.utils.translation import ugettext_lazy as _

from assets.const import AutomationTypes
from .change_secret import ChangeSecretAutomation

__all__ = ['CreateAccountAutomation']


class CreateAccountAutomation(ChangeSecretAutomation):
    username = models.CharField(max_length=128, blank=True, verbose_name=_("Username"))
    secret_type = models.CharField(max_length=16, verbose_name=_('Secret type'))
    secret_strategy = models.CharField(max_length=16, default=SecretPolicy.random,
                                       choices=SecretPolicy.choices, verbose_name=_("Secret strategy"))
    secret = models.CharField(max_length=1024, blank=True, verbose_name=_("Secret"))
    accounts = None

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.push_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Push asset account")
