from __future__ import unicode_literals

from django.apps import AppConfig


class OpsConfig(AppConfig):
    name = 'ops'

    def ready(self):
        from orgs.models import Organization
        from orgs.utils import set_current_org
        set_current_org(Organization.root())
        from .celery import signal_handler
        super().ready()
