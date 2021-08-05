from ..hands import *
from .base import BaseService

__all__ = ['BeatService']


class BeatService(BaseService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
