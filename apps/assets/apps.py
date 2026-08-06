from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssetsConfig(AppConfig):
    name = 'assets'
    verbose_name = _('App Assets')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def ready(self):
        from assets.const import AllTypes
        from . import signal_handlers  # noqa
        from . import tasks  # noqa
        AllTypes.reload_automation_methods()
        super().ready()
