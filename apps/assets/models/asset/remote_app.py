from django.utils.translation import gettext_lazy as _
from django.db import models

from .common import Asset


class RemoteApp(Asset):
    app_path = models.CharField(max_length=1024, verbose_name=_("App path"))
    attrs = models.JSONField(default=dict, verbose_name=_('Attrs'))
