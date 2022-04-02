from django.db import models
from django.utils.translation import gettext_lazy as _

from .application import Application


class Database(Application):
    host = models.CharField(max_length=1024, verbose_name=_('Host'))
    port = models.IntegerField(verbose_name=_("Port"))
    database = models.CharField(max_length=1024, blank=True, null=True, verbose_name=_("Database"))

    class Meta:
        verbose_name = _("Database")
