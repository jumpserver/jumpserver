from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PermsConfig(AppConfig):
    name = 'perms'
    verbose_name = _('App permissions')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
        from . import notifications  # noqa
        super().ready()
