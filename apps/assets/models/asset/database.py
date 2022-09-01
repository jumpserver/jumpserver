from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class Database(Asset):
    db_name = models.CharField(max_length=1024, verbose_name=_("Database"), blank=True)
    version = models.CharField(max_length=16, verbose_name=_("Version"), blank=True)

    def __str__(self):
        return '{}({}://{}/{})'.format(self.name, self.type, self.ip, self.db_name)

    class Meta:
        verbose_name = _("Database")
