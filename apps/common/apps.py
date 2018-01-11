from __future__ import unicode_literals

from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = 'common'

    def ready(self):
        from . import signals_handler
        from .signals import django_ready
        django_ready.send(self.__class__)
        return super().ready()
