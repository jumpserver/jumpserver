from django.core.management.base import BaseCommand
from .services.const import Services
from .services.utils import ServicesUtil


class Command(BaseCommand):
    help = 'Start services'

    def add_arguments(self, parser):
        parser.add_argument(
            'services',  nargs='+', choices=Services.values, default=Services.all, help='Service'
        )

    def handle(self, *args, **options):
        service_names = options.get('services')
        services = Services.get_services(service_names)
        util = ServicesUtil()
        util.start_and_watch(services)
        print('>>>>>>', options)
        print('>>>>>>', services)
        print('>>>>>>', service_names)
