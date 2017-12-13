from __future__ import unicode_literals

from django.apps import AppConfig


class AssetsConfig(AppConfig):
    name = 'assets'

    def ready(self):
        from .signals import on_app_ready
        from . import tasks
        on_app_ready.send(self.__class__)
        super().ready()
