from django.apps import AppConfig
from django.conf import settings
from django.contrib.auth import user_logged_in


class AuthenticationConfig(AppConfig):
    name = 'authentication'

    def ready(self):
        from . import signals_handlers
        if settings.ONLY_ALLOW_SINGLE_MACHINE_LOGIN:
            user_logged_in.connect(signals_handlers.on_user_auth_login_success)
        super().ready()

