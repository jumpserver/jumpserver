import os
import abc
from django.core.management.base import BaseCommand
from django.db.models import TextChoices
from .const import Services
from .utils import ServicesUtil


class Action(TextChoices):
    start = 'start', 'start'
    status = 'status', 'status'
    stop = 'stop', 'stop'
    restart = 'restart', 'restart'


class ServiceBaseCommand(BaseCommand):
    help = 'Service Base Command'

    action = None
    util = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            'services',  nargs='+', choices=Services.values, default=Services.all, help='Service',
        )
        parser.add_argument('-d', '--daemon', nargs="?", const=True)
        parser.add_argument('-w', '--worker', type=int, nargs="?", const=4)
        parser.add_argument('-f', '--force', nargs="?", const=True)

    def initial_util(self, *args, **options):
        service_names = options.get('services')
        service_kwargs = {
            'worker_g_unicorn': options.get('worker', 4)
        }
        services = Services.get_service_objects(service_names=service_names, **service_kwargs)

        kwargs = {
            'services': services,
            'daemon_run': options.get('daemon', False),
            'daemon_stop': Services.all.value in service_names,
            'force_stop': options.get('force', False),
        }
        self.util = ServicesUtil(**kwargs)

    def handle(self, *args, **options):
        assert self.action in Action.values, f'The action {self.action} is not in the optional list'
        _handle = getattr(self, f'_handle_{self.action}', lambda: None)
        _handle()

    def _handle_start(self):
        self.util.start_and_watch()
        os._exit(0)

    def _handle_stop(self):
        self.util.stop()

    def _handle_restart(self):
        self.util.restart()

    def _handle_status(self):
        self.util.show_status()
