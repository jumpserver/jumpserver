from django.db import models
from django.utils.translation import gettext_lazy as _

ADMIN = 'Admin'
USER = 'User'
AUDITOR = 'Auditor'


class Trigger(models.TextChoices):
    manual = 'manual', _('Manual trigger')
    timing = 'timing', _('Timing trigger')


class Status(models.TextChoices):
    ready = 'ready', _('Ready')
    pending = 'pending', _("Pending")
    running = 'running', _("Running")
    success = 'success', _("Success")
    failed = 'failed', _("Failed")
    error = 'error', _("Error")
    canceled = 'canceled', _("Canceled")
