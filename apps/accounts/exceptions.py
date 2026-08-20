from rest_framework import status

from common.exceptions import JMSException
from django.utils.translation import gettext_lazy as _


class VaultException(JMSException):
    default_detail = _(
        'Vault operation failed. Please retry or check your account information on Vault.'
    )


class VaultUnavailableException(VaultException):
    """The configured Vault service cannot be reached for a secret read."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = 'vault_unavailable'


class VaultAccountSyncUnavailableException(VaultException):
    """Vault is unavailable while synchronizing an account template."""

    default_code = 'vault_account_sync_unavailable'
    default_detail = _(
        'Vault service is unavailable. Unable to synchronize accounts. '
        'Please contact your administrator to check the Vault configuration.'
    )


class VaultSecretNotFoundException(VaultException):
    """The Vault entry or its secret field does not exist."""

    default_code = 'vault_secret_not_found'
    default_detail = _(
        'Secret not found in Vault. The local sync marker has been preserved.'
    )
