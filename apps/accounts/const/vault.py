from django.db import models
from django.utils.translation import gettext_lazy as _

__all__ = ['VaultTypeChoices']


class VaultTypeChoices(models.TextChoices):
    local = 'local', _('Database')
    hcp = 'hcp', _('HCP Vault')
    azure = 'azure', _('Azure Key Vault')
    aws = 'aws', _('Amazon Secrets Manager')
