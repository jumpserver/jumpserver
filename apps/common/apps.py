from __future__ import unicode_literals

import os
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

        if not os.environ.get('DJANGO_DEBUG_SHELL'):
            django_ready.send(CommonConfig)
