from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class Cloud(Asset):
    cluster = models.CharField(max_length=4096, verbose_name=_("Cluster"))

    def __str__(self):
        return self.name
