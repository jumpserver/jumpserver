from .services.command import ServiceBaseCommand
import time


class Command(ServiceBaseCommand):
    help = 'Start services'

    def _handle(self):
        stop_daemon = str(self.Services.all) in self.services_names
        self.services_util.restart(self.services, stop_daemon=stop_daemon)
