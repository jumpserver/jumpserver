import os
import shutil
from functools import wraps

from settings.api import settings


def cleanup_post_run(func):
    def get_instance(*args):
        if not len(args) > 0:
            return
        return args[0]

    @wraps(func)
    def wrapper(*args, **kwargs):
        instance = get_instance(*args)
        if not instance or not issubclass(type(instance), WorkPostRunCleaner):
            raise NotImplementedError("you should extend 'WorkPostRunCleaner'")
        try:
            return func(*args, **kwargs)
        finally:
            instance.clean_post_run()

    return wrapper


class WorkPostRunCleaner:
    @property
    def clean_dir(self):
        raise NotImplemented

    def clean_post_run(self):
        if settings.DEBUG_DEV:
            return
        if self.clean_dir and os.path.exists(self.clean_dir):
            shutil.rmtree(self.clean_dir)
