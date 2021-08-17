from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class TerminalConfig(AppConfig):
    name = 'terminal'
    verbose_name = _('Terminal')

    def ready(self):
        from . import signals_handler
        from . import notifications
        return super().ready()
