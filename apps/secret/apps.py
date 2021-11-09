from django.apps import AppConfig


class VaultConfig(AppConfig):
    name = 'secret'

    def ready(self):
        from .utils import init_vault_path
        from . import signals_handler
        # init_vault_path()
        return super().ready()
