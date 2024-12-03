from common.exceptions import JMSException
from django.utils.translation import gettext_lazy as _


class VaultException(JMSException):
    default_detail = _(
        'Vault operation failed. Please retry or check your account information on Vault.'
    )
