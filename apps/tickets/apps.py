from django.apps import AppConfig


class TicketsConfig(AppConfig):
    name = 'tickets'

    def ready(self):
        from . import signals_handler
        from . import notifications
        return super().ready()
