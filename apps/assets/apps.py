from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def initial_some_nodes():
    from .models import Node
    Node.initial_some_nodes()


def initial_some_nodes_callback(sender, **kwargs):
    initial_some_nodes()


class AssetsConfig(AppConfig):
    name = 'assets'

    def ready(self):
        super().ready()
        from . import signals_handler
        try:
            initial_some_nodes()
        except Exception:
            post_migrate.connect(initial_some_nodes_callback, sender=self)
