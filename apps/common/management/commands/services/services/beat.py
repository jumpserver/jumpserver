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
        scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
        cmd = [
            'celery', 'beat',
            '-A', 'ops',
            '-l', 'INFO',
            '--scheduler', scheduler,
            '--max-interval', '60'
        ]
        return cmd

    @property
    def cwd(self):
        return os.path.join(BASE_DIR, 'apps')

    def open_subprocess(self):
        # 分布式锁，解决多个服务启动多个beat处理定时任务的问题
        if not self.lock.acquire(timeout=10):
            print('No acquired beat distribute start lock', end='')
            return
        print("Get beat lock and start to run it", end='')
        super().open_subprocess()
        if self.lock.locked():
            self.lock.release()
