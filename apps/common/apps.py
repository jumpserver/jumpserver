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
        
        # Create JumpServer Client app
        from oauth2_provider.models import Application
        client_id = settings.OAUTH2_PROVIDER_CLIENT_ID
        if not Application.objects.filter(client_id=client_id).exists():
            Application.objects.create(
                name='JumpServer Client',
                client_id=client_id,
                client_type=Application.CLIENT_PUBLIC,
                authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
                redirect_uris=settings.OAUTH2_PROVIDER_CLIENT_REDIRECT_URI,
            )
