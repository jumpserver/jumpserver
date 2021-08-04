from .services.command import ServiceBaseCommand


class Command(ServiceBaseCommand):
    help = 'Show services status'

    def _handle(self):
        self.services_util.show_status(self.services)
