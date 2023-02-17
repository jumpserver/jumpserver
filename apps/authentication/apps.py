from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class AuthenticationConfig(AppConfig):
    name = 'authentication'
    verbose_name = _('Authentication')

    def ready(self):
        from . import signal_handlers
        from . import notifications
        from . import tasks

        super().ready()

