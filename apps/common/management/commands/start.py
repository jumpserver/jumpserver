import os
from .services.command import ServiceBaseCommand


class Command(ServiceBaseCommand):
    help = 'Start services'

    def _handle(self):
        self.services_util.start_and_watch(self.services, _daemon=self.daemon)
        os._exit(0)

