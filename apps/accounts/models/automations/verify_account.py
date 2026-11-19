from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from accounts.models.account import Account
from assets.const import Category
from .base import AccountBaseAutomation

__all__ = ['VerifyAccountAutomation']


def get_target_account_details(accounts):
    """Read only the display fields needed to identify an unavailable target."""
    return {
        str(account_id): {'asset_name': asset_name, 'username': username}
        for account_id, asset_name, username
        in accounts.values_list('id', 'asset__name', 'username')
    }


class VerifyAccountAutomation(AccountBaseAutomation):
    def filter_target_accounts(self, accounts):
        if not self.accounts:
            return accounts

        matches = Q(username__in=self.accounts)
        directory_matches = Q()
        for value in self.accounts:
            if '\\' in value:
                domain, _, username = value.partition('\\')
            else:
                username, _, domain = value.rpartition('@')
            if not username or not domain:
                continue

            directory_matches |= (
                Q(username__iexact=f'{username}@{domain}')
                | Q(username__iexact=f'{domain}\\{username}')
                | Q(username__iexact=username, asset__ds__domain_name__iexact=domain)
            )

        if directory_matches:
            matches |= Q(asset__platform__category=Category.DS, asset__ds__isnull=False) & directory_matches
        return accounts.filter(matches)

    def to_attr_json(self):
        snapshot = super().to_attr_json()
        assets = self.get_all_assets()
        accounts = Account.objects.filter(
            Q(asset__in=assets) | Q(asset__in=assets.values('directory_services')),
            is_active=True,
        )
        details = get_target_account_details(self.filter_target_accounts(accounts))
        snapshot['accounts'] = list(details)
        snapshot['target_account_details'] = details
        return snapshot

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.verify_account
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Verify asset account")
