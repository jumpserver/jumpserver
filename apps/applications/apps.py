from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    name = 'applications'
    verbose_name = _('Applications')

    def ready(self):
        from . import signal_handlers
        super().ready()
