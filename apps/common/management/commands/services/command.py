import abc
from django.core.management.base import BaseCommand
from .const import Services
from .utils import ServicesUtil


class ServiceBaseCommand(BaseCommand):
    Services = Services
    help = 'Service Base Command'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.services_util = ServicesUtil()
        self.services_names = []
        self.services = []
        self.force = False
        self.daemon = True

    def add_arguments(self, parser):
        parser.add_argument(
            'services',  nargs='+', choices=self.Services.values, default=self.Services.all,
            help='Service',
        )

    def handle(self, *args, **options):
        self.services_names = options.get('services')
        self.services = self.Services.get_services(self.services_names)
        self._handle()

    @abc.abstractmethod
    def _handle(self):
        pass
