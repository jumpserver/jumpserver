from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TerminalConfig(AppConfig):
    name = 'terminal'
    verbose_name = _('Terminals')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import notifications  # noqa
        from . import tasks  # noqa
        return super().ready()
