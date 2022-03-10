from __future__ import unicode_literals

import sys
from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = 'common'

    def ready(self):
        from . import signal_handlers
        from .signals import django_ready
        if 'migrate' in sys.argv or 'compilemessages' in sys.argv:
            return
        django_ready.send(CommonConfig)
