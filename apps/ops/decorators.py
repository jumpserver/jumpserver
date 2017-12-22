# -*- coding: utf-8 -*-
#
from functools import wraps


TASK_PREFIX = "TOOT"
CALLBACK_PREFIX = "COC"


def register_as_period_task(crontab=None, interval=None):
    """
    :param crontab:  "* * * * *"
    :param interval:  60*60*60
    :return:
    """
    from .utils import create_or_update_celery_periodic_tasks
    if crontab is None and interval is None:
        raise SyntaxError("Must set crontab or interval one")

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tasks = {
                func.__name__: {
                    'task': func.__name__,
                    'args': args,
                    'kwargs': kwargs,
                    'interval': interval,
                    'crontab': crontab,
                    'enabled': True,
                }
            }
            create_or_update_celery_periodic_tasks(tasks)
            return func(*args, **kwargs)
        return wrapper
    return decorate


