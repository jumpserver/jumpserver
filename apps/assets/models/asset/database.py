from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class Database(Asset):
    db_name = models.CharField(max_length=1024, verbose_name=_("Database"), blank=True)

    def __str__(self):
        return '{}({}://{}/{})'.format(self.name, self.type, self.address, self.db_name)

    @property
    def ip(self):
        return self.address

    @property
    def category_property(self):
        return {
            'db_name': self.db_name,
        }

    class Meta:
        verbose_name = _("Database")
