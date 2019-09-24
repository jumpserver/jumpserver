from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_save


class AuditsConfig(AppConfig):
    name = 'audits'

    def ready(self):
        from . import signals_handler
        if settings.SYSLOG_ENABLE:
            post_save.connect(signals_handler.on_audits_log_create)
