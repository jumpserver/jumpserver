from django.apps import AppConfig
from django.contrib.auth import user_logged_in
from jumpserver.const import CONFIG


class AuthenticationConfig(AppConfig):
    name = 'authentication'

    def ready(self):
        from . import signals_handlers
        if CONFIG.ONLY_ALLOW_SINGLE_MACHINE_LOGIN:
            user_logged_in.connect(signals_handlers.on_user_auth_login_success)
        super().ready()

