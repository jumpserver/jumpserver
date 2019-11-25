from __future__ import unicode_literals

from django.conf import settings
from django.apps import AppConfig


class PermsConfig(AppConfig):
    name = 'perms'

    def ready(self):
        from . import signals_handler
        if not settings.XPACK_ENABLED:
            settings.ASSETS_PERM_CACHE_ENABLE = False
        return super().ready()
