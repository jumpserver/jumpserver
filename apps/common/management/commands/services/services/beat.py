from ..hands import *
from .base import BaseService
from django.core.cache import cache


__all__ = ['BeatService']


class BeatService(BaseService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lock = cache.lock('beat-distribute-start-lock', expire=60)

    @property
    def cmd(self):
        print("\n- Start Beat as Periodic Task Scheduler")
        cmd = [
            sys.executable, 'start_celery_beat.py',
        ]
        return cmd

    @property
    def cwd(self):
        return os.path.join(BASE_DIR, 'utils')
