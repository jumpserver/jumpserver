from __future__ import unicode_literals

import sys
from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = 'common'

    def ready(self):
        from . import signals_handlers
        from .signals import django_ready
        if 'migrate' not in sys.argv:
            django_ready.send(CommonConfig)
