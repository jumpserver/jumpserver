import os

from .base import BaseService
from ..hands import *

__all__ = ['GunicornService']


class GunicornService(BaseService):

    def __init__(self, **kwargs):
        self.worker = kwargs.get('worker', 2)
        super().__init__(**kwargs)

    @property
    def cmd(self):
        print("\n- Start Gunicorn WSGI HTTP Server")

        log_format = '%(h)s %(t)s %(L)ss "%(r)s" %(s)s %(b)s '
        bind = f'{HTTP_HOST}:{HTTP_PORT}'
        jms_sock = os.path.join(BASE_DIR, 'data', 'unshare', 'jms.sock')
        bind_unix = f'unix:{jms_sock}'
        os.makedirs(os.path.dirname(jms_sock), exist_ok=True)

        cmd = [
            'gunicorn', 'jumpserver.asgi:application',
            '-b', bind,
            '-b', bind_unix,
            '-k', 'uvicorn.workers.UvicornWorker',
            '-w', str(self.worker),
            '--max-requests', '10240',
            '--max-requests-jitter', '2048',
            '--graceful-timeout', '30',
            '--access-logformat', log_format,
            '--access-logfile', '-'
        ]
        if DEBUG:
            cmd.append('--reload')
        return cmd

    @property
    def cwd(self):
        return APPS_DIR

    def start_other(self):
        from terminal.startup import CoreTerminal
        core_terminal = CoreTerminal()
        core_terminal.start_heartbeat_thread()
