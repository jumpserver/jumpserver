from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'users'
    verbose_name = _('Users')

    def ready(self):
        from . import signal_handlers
        from . import notifications
        from . import tasks
        super().ready()
