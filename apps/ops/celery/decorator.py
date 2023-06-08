# -*- coding: utf-8 -*-
#
from functools import wraps

_need_registered_period_tasks = []
_after_app_ready_start_tasks = []
_after_app_shutdown_clean_periodic_tasks = []


def add_register_period_task(task):
    _need_registered_period_tasks.append(task)


def get_register_period_tasks():
    return _need_registered_period_tasks


def add_after_app_shutdown_clean_task(name):
    _after_app_shutdown_clean_periodic_tasks.append(name)


def get_after_app_shutdown_clean_tasks():
    return _after_app_shutdown_clean_periodic_tasks


def add_after_app_ready_task(name):
    _after_app_ready_start_tasks.append(name)


def get_after_app_ready_tasks():
    return _after_app_ready_start_tasks


def register_as_period_task(
        crontab=None, interval=None, name=None,
        args=(), kwargs=None,
        description=''):
    """
    Warning: Task must have not any args and kwargs
    :param crontab:  "* * * * *"
    :param interval:  60*60*60
    :param args: ()
    :param kwargs: {}
    :param description: "
    :param name: ""
    :return:
    """
    if crontab is None and interval is None:
        raise SyntaxError("Must set crontab or interval one")

    def decorate(func):
        if crontab is None and interval is None:
            raise SyntaxError("Interval and crontab must set one")

        # Because when this decorator run, the task was not created,
        # So we can't use func.name
        task = '{func.__module__}.{func.__name__}'.format(func=func)
        _name = name if name else task
        add_register_period_task({
           _name: {
               'task': task,
               'interval': interval,
               'crontab': crontab,
               'args': args,
               'kwargs': kwargs if kwargs else {},
               'enabled': True,
               'description': description
           }
        })

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorate


def after_app_ready_start(func):
    # Because when this decorator run, the task was not created,
    # So we can't use func.name
    name = '{func.__module__}.{func.__name__}'.format(func=func)
    if name not in _after_app_ready_start_tasks:
        add_after_app_ready_task(name)

    @wraps(func)
    def decorate(*args, **kwargs):
        return func(*args, **kwargs)
    return decorate


def after_app_shutdown_clean_periodic(func):
    # Because when this decorator run, the task was not created,
    # So we can't use func.name
    name = '{func.__module__}.{func.__name__}'.format(func=func)
    if name not in _after_app_shutdown_clean_periodic_tasks:
        add_after_app_shutdown_clean_task(name)

    @wraps(func)
    def decorate(*args, **kwargs):
        return func(*args, **kwargs)
    return decorate
