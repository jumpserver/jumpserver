from __future__ import unicode_literals

from django.apps import AppConfig


class PermsConfig(AppConfig):
    name = 'perms'

    def ready(self):
        super().ready()
        from . import signals_handler
