from django.db.models import TextChoices
from django.core.management.base import BaseCommand, CommandError


class Services(TextChoices):
    gunicorn = 'gunicorn', 'gunicorn'
    daphne = 'daphne', 'daphne'
    celery_ansible = 'celery_ansible', 'celery_ansible'
    celery_default = 'celery_default', 'celery_default'
    beat = 'beat', 'beat'
    flower = 'flower', 'flower'
    web = 'web', 'web'
    celery = 'celery', 'celery'
    task = 'task', 'task'
    all = 'all', 'all'

    @classmethod
    def web_services(cls):
        return [cls.gunicorn, cls.daphne]

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
    def get_services(cls, names):
        services = set()
        for name in names:
            method_name = f'{name}_services'
            if hasattr(cls, method_name):
                _services = getattr(cls, method_name)()
            elif hasattr(cls, name):
                _services = [getattr(cls, name)]
            else:
                continue
            services.update(set(_services))
        return services


class ServicesUtil(object):

    @classmethod
    def start_services(cls, services):
        pass


class Command(BaseCommand):
    help = 'Start services'

    def add_arguments(self, parser):
        parser.add_argument(
            'services',  nargs='+', choices=Services.values, default=Services.all, help='Service'
        )

    def handle(self, *args, **options):
        service_names = options.get('services')
        services = Services.get_services(service_names)
        ServicesUtil.start_services(services)
        print('>>>>>>', options)
        print('>>>>>>', services)
