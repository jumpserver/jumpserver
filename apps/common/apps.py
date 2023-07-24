from __future__ import unicode_literals

import sys

from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = 'common'

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
        from .signals import django_ready
        excludes = ['migrate', 'compilemessages', 'makemigrations']
        for i in excludes:
            if i in sys.argv:
                return
        django_ready.send(CommonConfig)
