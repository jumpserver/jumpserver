from django.db.models import TextChoices
from django.core.management.base import BaseCommand, CommandError


class Services(TextChoices):
    gunicorn = 'gunicorn', 'gunicorn'
    daphne = 'daphne', 'daphne'
    celery_ansible = 'celery_ansible', 'celery_ansible'
    celery_default = 'celery_default', 'celery_default'
    beat = 'beat', 'beat'
    flower = 'flower', 'flower'

    @property
    def web(self):
        return [self.gunicorn.value, self.daphne.value]

    @property
    def celery(self):
        return [self.celery_ansible.value, self.celery_default.value]

    @property
    def task(self):
        return self.celery + [self.beat.value]

    @property
    def all(self):
        return self.__class__.values


class Command(BaseCommand):
    help = 'Start services'

    def add_arguments(self, parser):
        parser.add_argument('service', choices=Services.all, type=str, help='Service name')

    def handle(self, *args, **options):
        print('>>>>>>', options)
