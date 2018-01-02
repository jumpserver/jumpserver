from __future__ import unicode_literals

from django.apps import AppConfig


class TerminalConfig(AppConfig):
    name = 'terminal'

    def ready(self):
        from . import signals_handler
        return super().ready()