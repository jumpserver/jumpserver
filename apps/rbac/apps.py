from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RBACConfig(AppConfig):
    name = 'rbac'
    verbose_name = _('RBAC')

    def ready(self):
        from . import signal_handlers  # noqa
        super().ready()
