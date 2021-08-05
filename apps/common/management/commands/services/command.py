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
        self.worker = 4
        self.force = False
        self.daemon = True

    def add_arguments(self, parser):
        parser.add_argument(
            'services',  nargs='+', choices=self.Services.values, default=self.Services.all,
            help='Service',
        )
        parser.add_argument('-d', '--daemon', nargs="?", const=1)
        parser.add_argument('-w', '--worker', type=int, nargs="?", const=4)
        parser.add_argument('-f', '--force', nargs="?", const=1)

    def handle(self, *args, **options):
        self.daemon = options.get('daemon', False)
        self.worker = options.get('worker', 4)
        self.force = options.get('force', False)

        self.services_names = options.get('services')
        kwargs = {
            'worker': self.worker,
            'force': self.force,
            'daemon': self.daemon
        }
        self.services = self.Services.get_services(self.services_names, **kwargs)
        self._handle()

    @abc.abstractmethod
    def _handle(self):
        pass
