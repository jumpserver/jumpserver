from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = 'users'
    verbose_name = _('Users')

    def ready(self):
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
        from . import notifications  # noqa
        super().ready()
