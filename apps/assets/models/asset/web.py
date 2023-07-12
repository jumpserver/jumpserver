from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import FillType
from .common import Asset


class Web(Asset):
    autofill = models.CharField(max_length=16, choices=FillType.choices, default='basic', verbose_name=_("Autofill"))
    username_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Username selector"))
    password_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Password selector"))
    submit_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Submit selector"))
    script = models.JSONField(blank=True, default=list, verbose_name=_("Script"))

    class Meta:
        verbose_name = _("Web")
