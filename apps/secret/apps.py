from django.apps import AppConfig


class VaultConfig(AppConfig):
    name = 'secret'

    def ready(self):
        from . import signals_handler
        return super().ready()
