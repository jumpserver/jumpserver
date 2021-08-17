from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django.apps import AppConfig


class OpsConfig(AppConfig):
    name = 'ops'
    verbose_name = _('Operations')

    def ready(self):
        from orgs.models import Organization
        from orgs.utils import set_current_org
        set_current_org(Organization.root())
        from .celery import signal_handler
        from . import notifications
        super().ready()
