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
