from ..hands import *
from .base import BaseService

__all__ = ['FlowerService']


class FlowerService(BaseService):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def cmd(self):
        print("\n- Start Flower as Task Monitor")

        if os.getuid() == 0:
            os.environ.setdefault('C_FORCE_ROOT', '1')
        cmd = [
            'celery',
            '-A', 'ops',
            'flower',
            '-l', 'INFO',
            '--url_prefix=/core/flower',
            '--auto_refresh=False',
            '--max_tasks=1000',
            '--tasks_columns=uuid,name,args,state,received,started,runtime,worker'
        ]
        return cmd

    @property
    def cwd(self):
        return APPS_DIR
