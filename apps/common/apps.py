from __future__ import unicode_literals

import sys
from django.apps import AppConfig
from django.dispatch import receiver
from django.db.backends.signals import connection_created


@receiver(connection_created)
def on_db_connection_ready(sender, **kwargs):
    from .signals import django_ready
    if 'migrate' not in sys.argv:
        django_ready.send(CommonConfig)
        connection_created.disconnect(on_db_connection_ready)


class CommonConfig(AppConfig):
    name = 'common'

    def ready(self):
        from . import signals_handlers
