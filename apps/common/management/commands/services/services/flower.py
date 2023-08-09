from .base import BaseService
from ..hands import *

__all__ = ['FlowerService']


class FlowerService(BaseService):
    @property
    def cmd(self):
        print("\n- Start Flower as Task Monitor")

        if os.getuid() == 0:
            os.environ.setdefault('C_FORCE_ROOT', '1')
        cmd = [
            'celery',
            '-A', 'ops',
            'flower',
            '-logging=info',
            '--url_prefix=/core/flower',
            '--auto_refresh=False',
            '--max_tasks=1000',
            '--state_save_interval=600000'
        ]
        return cmd

    @property
    def cwd(self):
        return APPS_DIR
