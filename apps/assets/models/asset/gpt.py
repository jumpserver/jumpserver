from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class GPT(Asset):
    proxy = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Proxy"))

    class Meta:
        verbose_name = _("Web")
