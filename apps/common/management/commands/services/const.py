from .hands import *
from .services.gunicorn import GunicornService


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
    def get_services_object(cls, name):
        services_map = {
            cls.gunicorn.value: GunicornService
        }
        return services_map.get(name)

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

        service_objects = []
        for s in services:
            service_class = cls.get_services_object(s.value)
            if not service_class:
                continue
            service_objects.append(service_class())
        return service_objects
