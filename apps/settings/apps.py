from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SettingsConfig(AppConfig):
    name = 'settings'
    verbose_name = _('Settings')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
