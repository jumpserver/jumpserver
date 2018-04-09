from __future__ import unicode_literals

from django.apps import AppConfig


class OpsConfig(AppConfig):
    name = 'ops'

    def ready(self):
        super().ready()
        from .celery import signal_handler
