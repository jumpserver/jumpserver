from django.apps import AppConfig


class OrgsConfig(AppConfig):
    name = 'orgs'

    def ready(self):
        from . import signals_handler
