from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TicketsConfig(AppConfig):
    name = 'tickets'
    verbose_name = _('Tickets')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import notifications  # noqa
        return super().ready()
