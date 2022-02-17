from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class PermsConfig(AppConfig):
    name = 'perms'
    verbose_name = _('Permissions')

    def ready(self):
        super().ready()
        from . import signals_handler
        from . import notifications
