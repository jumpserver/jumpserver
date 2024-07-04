from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils import load_country_calling_codes_from_file


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


class Language(models.TextChoices):
    en = 'en', 'English'
    zh_hans = 'zh-hans', '中文(简体)'
    zh_hant = 'zh-hant', '中文(繁體)'
    jp = 'ja', '日本語',


COUNTRY_CALLING_CODES = load_country_calling_codes_from_file()
