from django.conf import settings
from django.utils.translation import gettext_lazy as _

from accounts.const import AutomationTypes, SecretType
from accounts.models import Account
from .base import AccountBaseAutomation, ChangeSecretMixin
from .change_secret import BaseSecretRecord

__all__ = ['PushAccountAutomation', 'PushSecretRecord']


class PushAccountAutomation(ChangeSecretMixin, AccountBaseAutomation):

    def gen_nonlocal_accounts(self, usernames, asset):
        secret_type = self.secret_type
        account_usernames = asset.accounts \
            .filter(secret_type=self.secret_type) \
            .values_list('username', flat=True)
        create_usernames = set(usernames) - set(account_usernames)

        create_accounts = [
            Account(
                name=f"{username}-{secret_type}" if secret_type != SecretType.PASSWORD else username,
                username=username, secret=self.get_secret(),
                secret_type=secret_type, asset=asset,
            )
            for username in create_usernames
        ]
        return create_accounts

    def save(self, *args, **kwargs):
        self.type = AutomationTypes.push_account
        if not settings.XPACK_LICENSE_IS_VALID:
            self.is_periodic = False
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Push asset account")


class PushSecretRecord(BaseSecretRecord):
    class Meta:
        verbose_name = _("Push secret record")
