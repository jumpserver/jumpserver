from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SettingsConfig(AppConfig):
    name = 'settings'
    verbose_name = _('App Settings')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
        from .models import init_sqlite_db, register_sqlite_connection
        try:
            init_sqlite_db()
            register_sqlite_connection()
        except Exception:
            pass
