from __future__ import unicode_literals

import os
import sys

from django.apps import AppConfig
from django.db import close_old_connections
from django.conf import settings


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
            close_old_connections()
        
        from authentication.backends.oauth2_provider import utils
        utils.get_or_create_jumpserver_client_application()
