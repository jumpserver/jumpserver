from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _


class Connectivity(TextChoices):
    unknown = 'unknown', _('Unknown')
    ok = 'ok', _('Ok')
    failed = 'failed', _('Failed')


class SecretType(TextChoices):
    password = 'password', _('Password')
    ssh_key = 'ssh_key', _('SSH key')
    access_key = 'access_key', _('Access key')
    token = 'token', _('Token')
