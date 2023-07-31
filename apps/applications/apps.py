from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ApplicationsConfig(AppConfig):
    name = 'applications'
    verbose_name = _('Applications')

    def ready(self):
        super().ready()
