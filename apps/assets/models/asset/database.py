from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class Database(Asset):
    db_name = models.CharField(max_length=1024, verbose_name=_("Database"), blank=True)

    class Meta:
        verbose_name = _("Database")
