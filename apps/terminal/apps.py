from __future__ import unicode_literals

from django.apps import AppConfig


class TerminalConfig(AppConfig):
    name = 'terminal'

    def ready(self):
        from .signals import on_app_ready
        on_app_ready.send(self.__class__)
        super().ready()
