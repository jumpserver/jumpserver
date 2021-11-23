# -*- coding: utf-8 -*-
#
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class Connectivity(TextChoices):
    unknown = 'unknown', _('Unknown')
    ok = 'ok', _('Ok')
    failed = 'failed', _('Failed')


class StorageType(TextChoices):
    db = 'db', _('DB storage')
    vault = 'vault', _('Vault storage')
    pam = 'pam', _('Pam storage')
