from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import ugettext_lazy as _


class AccountsConfig(AppConfig):
    name = 'accounts'
    verbose_name = _('Account Management')

    def ready(self):
        super().ready()
        from accounts.models.initial_db import initial_account_type
        post_migrate.connect(initial_account_type, sender=self)
