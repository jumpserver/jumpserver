from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from accounts.models.account import Account
from .base import AccountBaseAutomation

__all__ = ['VerifyAccountAutomation']


class VerifyAccountAutomation(AccountBaseAutomation):
    def to_attr_json(self):
        snapshot = super().to_attr_json()
        assets = self.get_all_assets()
        accounts = Account.objects.filter(
            Q(asset__in=assets) | Q(asset__in=assets.values('directory_services')),
            is_active=True,
        )
        if self.accounts:
            accounts = accounts.filter(username__in=self.accounts)
        snapshot['accounts'] = [str(pk) for pk in accounts.values_list('id', flat=True)]
        return snapshot

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.verify_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Verify asset account")
