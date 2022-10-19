from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class Web(Asset):
    autofill = models.CharField(max_length=16, default='basic')
    username_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Username selector"))
    password_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Password selector"))
    submit_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Submit selector"))
