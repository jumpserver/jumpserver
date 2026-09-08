from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.const import FillType
from .common import Asset


class Web(Asset):
    allowed_urls = models.JSONField(blank=True, default=list, verbose_name=_("Allowed sites"))
    autofill = models.CharField(max_length=16, choices=FillType.choices, default='basic', verbose_name=_("Autofill"))
    username_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Username selector"))
    password_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Password selector"))
    submit_selector = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Submit selector"))
    success_selector = models.CharField(
        max_length=128, blank=True, default='', verbose_name=_("Success selector"),
        help_text=_(
            "Selector for an element that appears only after a successful login, e.g. css=#dashboard. "
            "Required for basic autofill."
        )
    )
    interactive_selector = models.CharField(
        max_length=128, blank=True, default='', verbose_name=_("Interactive selector"),
        help_text=_("Optional interactive verification area, e.g. css=#mfa-dialog. Exclude credentials and password visibility controls.")
    )
    script = models.JSONField(blank=True, default=list, verbose_name=_("Script"))

    class Meta:
        verbose_name = _("Web")
