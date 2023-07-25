from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OrgsConfig(AppConfig):
    name = 'orgs'
    verbose_name = _('App organizations')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
        super().ready()
