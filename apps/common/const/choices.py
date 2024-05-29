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


COUNTRY_CALLING_CODES = [
    {'name': 'China(中国)', 'value': '+86'},
    {'name': 'HongKong(中国香港)', 'value': '+852'},
    {'name': 'Macao(中国澳门)', 'value': '+853'},
    {'name': 'Taiwan(中国台湾)', 'value': '+886'},
    {'name': 'America(America)', 'value': '+1'},
    {'name': 'Russia(Россия)', 'value': '+7'},
    {'name': 'France(français)', 'value': '+33'},
    {'name': 'Britain(Britain)', 'value': '+44'},
    {'name': 'Germany(Deutschland)', 'value': '+49'},
    {'name': 'Japan(日本)', 'value': '+81'},
    {'name': 'Korea(한국)', 'value': '+82'},
    {'name': 'India(भारत)', 'value': '+91'}
]
