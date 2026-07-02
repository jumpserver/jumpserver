from __future__ import unicode_literals

import os
import sys

from django.apps import AppConfig
from django.db import close_old_connections


class CommonConfig(AppConfig):
    name = 'common'

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
        from .signals import django_ready

        excludes = [
            'migrate', 'compilemessages', 'makemigrations', 
            'check', 'makemessages', 'upgrade_db', 'collect_static',
        ]
        for i in excludes:
            if i in sys.argv:
                return

        django_ready.send(CommonConfig)
        close_old_connections()
