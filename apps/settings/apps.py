from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SettingsConfig(AppConfig):
    name = 'settings'
    verbose_name = _('Settings')

    def ready(self):
        from . import tasks
        from . import signal_handlers
