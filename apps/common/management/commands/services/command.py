import multiprocessing

from django.core.management.base import BaseCommand
from django.db.models import TextChoices

from .hands import *
from .utils import ServicesUtil


class Services(TextChoices):
    gunicorn = 'gunicorn', 'gunicorn'
    celery_ansible = 'celery_ansible', 'celery_ansible'
    celery_default = 'celery_default', 'celery_default'
    beat = 'beat', 'beat'
    flower = 'flower', 'flower'
    ws = 'ws', 'ws'
    web = 'web', 'web'
    celery = 'celery', 'celery'
    task = 'task', 'task'
    all = 'all', 'all'

    @classmethod
    def get_service_object_class(cls, name):
        from . import services
        services_map = {
            cls.gunicorn.value: services.GunicornService,
            cls.flower: services.FlowerService,
            cls.celery_default: services.CeleryDefaultService,
            cls.celery_ansible: services.CeleryAnsibleService,
            cls.beat: services.BeatService
        }
        return services_map.get(name)

    @classmethod
    def web_services(cls):
        return [cls.gunicorn, cls.flower]

    @classmethod
    def celery_services(cls):
        return [cls.celery_ansible, cls.celery_default]

    @classmethod
    def task_services(cls):
        return cls.celery_services() + [cls.beat]

    @classmethod
    def all_services(cls):
        return cls.web_services() + cls.task_services()

    @classmethod
    def export_services_values(cls):
        return [cls.all.value, cls.web.value, cls.task.value] + [s.value for s in cls.all_services()]

    @classmethod
    def get_service_objects(cls, service_names, **kwargs):
        services = set()
        for name in service_names:
            method_name = f'{name}_services'
            if hasattr(cls, method_name):
                _services = getattr(cls, method_name)()
            elif hasattr(cls, name):
                _services = [getattr(cls, name)]
            else:
                continue
            services.update(set(_services))

        service_objects = []
        for s in services:
            service_class = cls.get_service_object_class(s.value)
            if not service_class:
                continue
            kwargs.update({
                'name': s.value
            })
            service_object = service_class(**kwargs)
            service_objects.append(service_object)
        return service_objects


class Action(TextChoices):
    start = 'start', 'start'
    status = 'status', 'status'
    stop = 'stop', 'stop'
    restart = 'restart', 'restart'


class BaseActionCommand(BaseCommand):
    help = 'Service Base Command'

    action = None
    util = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument(
            'services', nargs='+', choices=Services.export_services_values(), help='Service',
        )
        parser.add_argument('-d', '--daemon', nargs="?", const=True)
        parser.add_argument('-w', '--worker', type=int, nargs="?", default=4)
        parser.add_argument('-f', '--force', nargs="?", const=True)

    def initial_util(self, *args, **options):
        service_names = options.get('services')
        service_kwargs = {
            'worker_gunicorn': options.get('worker')
        }
        services = Services.get_service_objects(service_names=service_names, **service_kwargs)

        kwargs = {
            'services': services,
            'run_daemon': options.get('daemon', False),
            'stop_daemon': self.action == Action.stop.value and Services.all.value in service_names,
            'force_stop': options.get('force') or False,
        }
        self.util = ServicesUtil(**kwargs)

    def handle(self, *args, **options):
        self.initial_util(*args, **options)
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
