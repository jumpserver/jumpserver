from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'App Accounts'

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
