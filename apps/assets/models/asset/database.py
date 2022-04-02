from django.db import models
from django.utils.translation import ugettext_lazy as _

from .common import Asset


class Database(Asset):
    database = models.CharField(max_length=1024, verbose_name=_("Database"), blank=True)

