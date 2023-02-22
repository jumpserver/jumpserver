from django.utils.translation import gettext_lazy as _

from .common import Asset


class Cloud(Asset):
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Cloud")
