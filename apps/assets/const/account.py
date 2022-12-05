from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _


class Connectivity(TextChoices):
    UNKNOWN = 'unknown', _('Unknown')
    OK = 'ok', _('Ok')
    FAILED = 'failed', _('Failed')


class SecretType(TextChoices):
    PASSWORD = 'password', _('Password')
    SSH_KEY = 'ssh_key', _('SSH key')
    ACCESS_KEY = 'access_key', _('Access key')
    TOKEN = 'token', _('Token')
