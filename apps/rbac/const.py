from django.db import models
from django.utils.translation import ugettext_lazy as _


class ScopeChoices(models.TextChoices):
    system = 'system', _('System')
    org = 'org', _('Organization')
