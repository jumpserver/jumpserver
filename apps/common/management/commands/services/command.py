import abc
from django.core.management.base import BaseCommand
from .const import Services
from .utils import ServicesUtil


class ServiceBaseCommand(BaseCommand):
    help = 'Service Base Command'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.services_util = ServicesUtil()
        self.services = []

    def add_arguments(self, parser):
        parser.add_argument(
            'services',  nargs='+', choices=Services.values, default=Services.all, help='Service'
        )

    def handle(self, *args, **options):
        service_names = options.get('services')
        services = Services.get_services(service_names)
        self.services = list(services)
        self._handle()

    @abc.abstractmethod
    def _handle(self):
        pass
