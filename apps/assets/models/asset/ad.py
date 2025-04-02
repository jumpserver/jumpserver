from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset

__all__ = ['AD']


class AD(Asset):
    domain_name = models.CharField(max_length=128, blank=True, default='', verbose_name=_("Domain name"))

    class Meta:
        verbose_name = _("Active Directory")
