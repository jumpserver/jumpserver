# ~*~ coding: utf-8 ~*~

import os
import json
from functools import wraps

from celery import Celery, subtask
from celery.signals import worker_ready, worker_shutdown
from django.db.utils import ProgrammingError, OperationalError

from .utils import get_logger

logger = get_logger(__file__)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jumpserver.settings')

from django.conf import settings
from django.core.cache import cache

app = Celery('jumpserver')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: [app_config.split('.')[0] for app_config in settings.INSTALLED_APPS])


def create_or_update_celery_periodic_tasks(tasks):
    from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
    """
    :param tasks: {
        'add-every-monday-morning': {
            'task': 'tasks.add' # A registered celery task,
            'interval': 30,
            'crontab': "30 7 * * *",
            'args': (16, 16),
            'kwargs': {},
            'enabled': False,
        },
    }
    :return:
    """
    # Todo: check task valid, task and callback must be a celery task
    for name, detail in tasks.items():
        interval = None
        crontab = None
        try:
            IntervalSchedule.objects.all().count()
        except (ProgrammingError, OperationalError):
            return None

        if isinstance(detail.get("interval"), int):
            intervals = IntervalSchedule.objects.filter(
                every=detail["interval"], period=IntervalSchedule.SECONDS
            )
            if intervals:
                interval = intervals[0]
            else:
                interval = IntervalSchedule.objects.create(
                    every=detail['interval'],
                    period=IntervalSchedule.SECONDS,
                )
        elif isinstance(detail.get("crontab"), str):
            try:
                minute, hour, day, month, week = detail["crontab"].split()
            except ValueError:
                raise SyntaxError("crontab is not valid")
            kwargs = dict(
                minute=minute, hour=hour, day_of_week=week,
                day_of_month=day, month_of_year=month,
            )
            contabs = CrontabSchedule.objects.filter(
                **kwargs
            )
            if contabs:
                crontab = contabs[0]
            else:
                crontab = CrontabSchedule.objects.create(**kwargs)
        else:
            raise SyntaxError("Schedule is not valid")

        defaults = dict(
            interval=interval,
            crontab=crontab,
            name=name,
            task=detail['task'],
            args=json.dumps(detail.get('args', [])),
            kwargs=json.dumps(detail.get('kwargs', {})),
            enabled=detail.get('enabled', True),
        )

        task = PeriodicTask.objects.update_or_create(
            defaults=defaults, name=name,
        )
        return task


def disable_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=task_name).update(enabled=False)


def delete_celery_periodic_task(task_name):
    from django_celery_beat.models import PeriodicTask
    PeriodicTask.objects.filter(name=task_name).delete()


__REGISTER_PERIODIC_TASKS = []
__AFTER_APP_SHUTDOWN_CLEAN_TASKS = []
__AFTER_APP_READY_RUN_TASKS = []


def register_as_period_task(crontab=None, interval=None):
    """
    Warning: Task must be have not any args and kwargs
    :param crontab:  "* * * * *"
    :param interval:  60*60*60
    :return:
    """
    if crontab is None and interval is None:
        raise SyntaxError("Must set crontab or interval one")

    def decorate(func):
        if crontab is None and interval is None:
            raise SyntaxError("Interval and crontab must set one")

        # Because when this decorator run, the task was not created,
        # So we can't use func.name
        name = '{func.__module__}.{func.__name__}'.format(func=func)
        if name not in __REGISTER_PERIODIC_TASKS:
            create_or_update_celery_periodic_tasks({
                name: {
                    'task': name,
                    'interval': interval,
                    'crontab': crontab,
                    'args': (),
                    'enabled': True,
                }
            })
            __REGISTER_PERIODIC_TASKS.append(name)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorate


def after_app_ready_start(func):
    # Because when this decorator run, the task was not created,
    # So we can't use func.name
    name = '{func.__module__}.{func.__name__}'.format(func=func)
    if name not in __AFTER_APP_READY_RUN_TASKS:
        __AFTER_APP_READY_RUN_TASKS.append(name)

    @wraps(func)
    def decorate(*args, **kwargs):
        return func(*args, **kwargs)

    return decorate


def after_app_shutdown_clean(func):
    # Because when this decorator run, the task was not created,
    # So we can't use func.name
    name = '{func.__module__}.{func.__name__}'.format(func=func)
    if name not in __AFTER_APP_READY_RUN_TASKS:
        __AFTER_APP_SHUTDOWN_CLEAN_TASKS.append(name)

    @wraps(func)
    def decorate(*args, **kwargs):
        return func(*args, **kwargs)

    return decorate


@worker_ready.connect
def on_app_ready(sender=None, headers=None, body=None, **kwargs):
    if cache.get("CELERY_APP_READY", 0) == 1:
        return
    cache.set("CELERY_APP_READY", 1, 10)
    logger.debug("App ready signal recv")
    logger.debug("Start need start task: [{}]".format(
        ", ".join(__AFTER_APP_READY_RUN_TASKS))
    )
    for task in __AFTER_APP_READY_RUN_TASKS:
        subtask(task).delay()


@worker_shutdown.connect
def after_app_shutdown(sender=None, headers=None, body=None, **kwargs):
    if cache.get("CELERY_APP_SHUTDOWN", 0) == 1:
        return
    cache.set("CELERY_APP_SHUTDOWN", 1, 10)
    from django_celery_beat.models import PeriodicTask
    logger.debug("App shutdown signal recv")
    logger.debug("Clean need cleaned period tasks: [{}]".format(
        ', '.join(__AFTER_APP_SHUTDOWN_CLEAN_TASKS))
    )
    PeriodicTask.objects.filter(name__in=__AFTER_APP_SHUTDOWN_CLEAN_TASKS).delete()
