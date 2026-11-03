from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TicketsConfig(AppConfig):
    name = 'tickets'
    verbose_name = _('App Tickets')

    def ready(self):
        from .plugins import ticket_plugins
        ticket_plugins.discover()
        ticket_plugins.validate()
        from . import signal_handlers  # noqa
        from . import notifications  # noqa
        from . import tasks  # noqa
        return super().ready()
