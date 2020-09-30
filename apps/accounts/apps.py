from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        super().ready()
        from accounts.models.initial_db import initial_account_type
        post_migrate.connect(initial_account_type, sender=self)
