from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset


class Cloud(Asset):
    namespace = models.CharField(max_length=1024, verbose_name=_("Namespace"), blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Cloud")
