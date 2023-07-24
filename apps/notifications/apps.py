from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NotificationsConfig(AppConfig):
    name = 'notifications'
    verbose_name = _('Notifications')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import notifications  # noqa
        super().ready()
