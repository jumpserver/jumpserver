from django.utils.translation import gettext_lazy as _
from django.db import models

from .common import Asset


class Web(Asset):
    url = models.CharField(max_length=1024, verbose_name=_("url"))
