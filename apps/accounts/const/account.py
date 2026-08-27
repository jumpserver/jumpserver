from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class SecretType(TextChoices):
    PASSWORD = 'password', _('Password')
    SSH_KEY = 'ssh_key', _('SSH key')
    SSH_CERTIFICATE = 'ssh_certificate', _('SSH certificate')
    ACCESS_KEY = 'access_key', _('Access key')
    TOKEN = 'token', _('Token')
    API_KEY = 'api_key', _("API key")


class AliasAccount(TextChoices):
    ALL = '@ALL', _('All')
    INPUT = '@INPUT', _('Manual input')
    USER = '@USER', _('Dynamic user')
    ANON = '@ANON', _('Anonymous account')
    SPEC = '@SPEC', _('Specified account')

    @classmethod
    def virtual_choices(cls):
        return [(k, v) for k, v in cls.choices if k not in (cls.ALL,)]


class Source(TextChoices):
    LOCAL = 'local', _('Local')
    DISCOVERY = 'collected', _('Discovery')
    TEMPLATE = 'template', _('Template')
    CREDENTIAL_LEASE = 'credential_lease', _('Credential lease')


class AccountInvalidPolicy(TextChoices):
    SKIP = 'skip', _('Skip')
    UPDATE = 'update', _('Update')
    ERROR = 'error', _('Failed')
