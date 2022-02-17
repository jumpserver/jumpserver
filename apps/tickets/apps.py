from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class TicketsConfig(AppConfig):
    name = 'tickets'
    verbose_name = _('Tickets')

    def ready(self):
        from . import signals_handler
        from . import notifications
        return super().ready()
