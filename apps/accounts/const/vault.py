from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ['VaultType']


class VaultType(models.TextChoices):
    LOCAL = 'local', _('Local')
    HCP = 'hcp', _('HCP vault')
