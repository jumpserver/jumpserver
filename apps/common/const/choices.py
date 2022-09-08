from django.db import models
from django.utils.translation import ugettext_lazy as _

ADMIN = 'Admin'
USER = 'User'
AUDITOR = 'Auditor'


class Trigger(models.TextChoices):
    manual = 'manual', _('Manual trigger')
    timing = 'timing', _('Timing trigger')
