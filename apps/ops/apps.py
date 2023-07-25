from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OpsConfig(AppConfig):
    name = 'ops'
    verbose_name = _('App ops')

    def ready(self):
        from orgs.models import Organization
        from orgs.utils import set_current_org
        set_current_org(Organization.root())
        from .celery import signal_handler  # noqa
        from . import signal_handlers  # noqa
        from . import notifications  # noqa
        from . import tasks  # noqa
        super().ready()
