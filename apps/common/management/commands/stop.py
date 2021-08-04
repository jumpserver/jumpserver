from .services.command import ServiceBaseCommand


class Command(ServiceBaseCommand):
    help = 'Stop services'

    def _handle(self):
        self.services_util.stop(self.services)
