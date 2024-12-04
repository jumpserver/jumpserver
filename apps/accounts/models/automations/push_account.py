from django.conf import settings
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes
from accounts.models import Account
from .base import AccountBaseAutomation
from .change_secret import ChangeSecretMixin

__all__ = ['PushAccountAutomation']


class PushAccountAutomation(ChangeSecretMixin, AccountBaseAutomation):

    def create_nonlocal_accounts(self, usernames, asset):
        secret_type = self.secret_type
        account_usernames = asset.accounts \
            .filter(secret_type=self.secret_type) \
            .values_list('username', flat=True)
        create_usernames = set(usernames) - set(account_usernames)
        create_account_objs = [
            Account(
                name=f'{username}-{secret_type}', username=username,
                secret_type=secret_type, asset=asset,
            )
            for username in create_usernames
        ]
        Account.objects.bulk_create(create_account_objs)

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.push_account
        if not settings.XPACK_LICENSE_IS_VALID:
            self.is_periodic = False
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Push asset account")
