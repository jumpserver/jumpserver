from django.apps import AppConfig


class AuditsConfig(AppConfig):
    name = 'audits'

    def ready(self):
        from . import signals_handler
