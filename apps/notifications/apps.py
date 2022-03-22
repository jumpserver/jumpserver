from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class NotificationsConfig(AppConfig):
    name = 'notifications'
    verbose_name = _('Notifications')

    def ready(self):
        from . import signal_handlers
        from . import notifications
        super().ready()
