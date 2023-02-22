from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class TerminalConfig(AppConfig):
    name = 'terminal'
    verbose_name = _('Terminals')

    def ready(self):
        from . import signal_handlers
        from . import notifications
        from . import tasks
        return super().ready()
