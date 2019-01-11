# -*- coding: utf-8 -*-
#
from functools import wraps

_need_registered_period_tasks = []
_after_app_ready_start_tasks = []
_after_app_shutdown_clean_periodic_tasks = []


def add_register_period_task(task):
    _need_registered_period_tasks.append(task)
    # key = "__REGISTER_PERIODIC_TASKS"
    # value = cache.get(key, [])
    # value.append(name)
    # cache.set(key, value)


def get_register_period_tasks():
    # key = "__REGISTER_PERIODIC_TASKS"
    # return cache.get(key, [])
    return _need_registered_period_tasks


def add_after_app_shutdown_clean_task(name):
    # key = "__AFTER_APP_SHUTDOWN_CLEAN_TASKS"
    # value = cache.get(key, [])
    # value.append(name)
    # cache.set(key, value)
    _after_app_shutdown_clean_periodic_tasks.append(name)


def get_after_app_shutdown_clean_tasks():
    # key = "__AFTER_APP_SHUTDOWN_CLEAN_TASKS"
    # return cache.get(key, [])
    return _after_app_shutdown_clean_periodic_tasks


def add_after_app_ready_task(name):
    # key = "__AFTER_APP_READY_RUN_TASKS"
    # value = cache.get(key, [])
    # value.append(name)
    # cache.set(key, value)
    _after_app_ready_start_tasks.append(name)


def get_after_app_ready_tasks():
    # key = "__AFTER_APP_READY_RUN_TASKS"
    # return cache.get(key, [])
    return _after_app_ready_start_tasks


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
        add_register_period_task({
           name: {
               'task': name,
               'interval': interval,
               'crontab': crontab,
               'args': (),
               'enabled': True,
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
