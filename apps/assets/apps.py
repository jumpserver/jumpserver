from __future__ import unicode_literals

from django.apps import AppConfig


class AssetsConfig(AppConfig):
    name = 'assets'

    def ready(self):
        super().ready()
        from . import signals_handler
        from .models import Node
        Node.initial_some_nodes()
